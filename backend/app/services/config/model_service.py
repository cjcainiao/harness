# 模型配置业务

import os
import re
from copy import deepcopy
from typing import Any
from urllib.parse import parse_qsl, urlsplit

from ruamel.yaml import YAML
from ruamel.yaml.comments import CommentedMap, CommentedSeq
from ruamel.yaml.error import YAMLError

from app.schemas.config.model_schema import ModelConfigInfo
from harness.config.app_config import AppConfig, get_app_config, reload_app_config
from harness.config.model_config import ModelConfig
from harness.utils.yaml_util import edit_yaml_text, render_yaml_fragment, yaml_block_end


_env_reference = re.compile(r"\$(?:([A-Za-z_][A-Za-z0-9_]*)|\{([A-Za-z_][A-Za-z0-9_]*)\})")
_secret_query_name = re.compile(r"(?:api[_-]?key|token|secret|password|credential|auth)", re.I)


# 获取不含连接凭据的模型配置
def list_model_configs() -> list[ModelConfigInfo]:
    result: list[ModelConfigInfo] = []
    for model in get_app_config().models:
        extra = model.model_extra or {}
        result.append(
            ModelConfigInfo(
                model_name=model.model_name,
                display_name=model.display_name or model.model_name,
                description=model.description,
                provider=model.provider,
                use=model.use,
                base_url_configured=bool(extra.get("base_url")),
                api_key_configured=bool(extra.get("api_key")),
                timeout=extra.get("timeout"),
                max_retries=extra.get("max_retries"),
                max_tokens=extra.get("max_tokens"),
                supports_thinking=model.supports_thinking,
                reasoning_levels=model.reasoning_levels,
                when_thinking_enabled=model.when_thinking_enabled,
                when_thinking_disabled=model.when_thinking_disabled,
                supports_vision=model.supports_vision,
                context_window=model.context_window,
            )
        )
    return result


# 校验并整理提交的模型字段
def _prepare_model_changes(values: dict[str, Any]) -> dict[str, Any]:
    prepared = dict(values)
    for field in ("model_name", "provider", "use"):
        if field not in prepared:
            continue
        if not isinstance(prepared[field], str):
            raise ValueError("模型必填字段不能设为空")
        value = prepared[field].strip()
        if not value or value.startswith("$"):
            raise ValueError("模型必填字段不能为空或引用环境变量")
        prepared[field] = value
    if prepared.get("display_name") is not None:
        prepared["display_name"] = prepared["display_name"].strip()
        if not prepared["display_name"] or prepared["display_name"].startswith("$"):
            raise ValueError("模型显示名称不能为空或引用环境变量")
    if isinstance(prepared.get("description"), str) and prepared["description"].startswith("$"):
        raise ValueError("模型描述不能引用环境变量")

    if "use" in prepared and not re.fullmatch(
        r"[A-Za-z_][A-Za-z0-9_]*(?:\.[A-Za-z_][A-Za-z0-9_]*)*:[A-Za-z_][A-Za-z0-9_]*",
        prepared["use"],
    ):
        raise ValueError("模型实现类路径格式无效")

    api_key = prepared.get("api_key")
    if api_key is not None:
        match = _env_reference.fullmatch(api_key)
        if match is None:
            raise ValueError("服务密钥必须引用环境变量")
        variable = match.group(1) or match.group(2)
        if not os.getenv(variable):
            raise ValueError("服务密钥引用的环境变量不可用")
        prepared["api_key"] = f"${variable}"

    base_url = prepared.get("base_url")
    if base_url is not None:
        base_url = base_url.strip()
        if base_url.startswith("$"):
            match = _env_reference.fullmatch(base_url)
            if match is None:
                raise ValueError("服务地址环境变量引用格式无效")
            variable = match.group(1) or match.group(2)
            base_url = f"${variable}"
        prepared["base_url"] = base_url
        resolved_url = AppConfig.resolve_env_variables(base_url)
        parsed = urlsplit(resolved_url)
        if parsed.scheme not in {"http", "https"} or not parsed.netloc:
            raise ValueError("服务地址格式无效")
        if parsed.username or parsed.password or any(
            _secret_query_name.search(key) for key, _ in parse_qsl(parsed.query)
        ):
            raise ValueError("服务地址不能直接包含凭据")

    if any(
        prepared.get(field) is None
        for field in ("provider", "use", "supports_thinking", "reasoning_levels", "supports_vision")
        if field in prepared
    ):
        raise ValueError("模型必填字段不能设为空")
    return prepared


# 校验新增模型的完整配置
def _prepare_model_values(values: dict[str, Any]) -> dict[str, Any]:
    prepared = _prepare_model_changes(values)
    resolved = AppConfig.resolve_env_variables(prepared)
    ModelConfig.model_validate(resolved)
    return prepared


# 对齐模型列表项缩进
def _indent_model_fragment(fragment: str, offset: int) -> str:
    adjusted: list[str] = []
    for line in fragment.splitlines(keepends=True):
        if not line.strip():
            adjusted.append(line)
            continue
        indent = len(line) - len(line.lstrip(" "))
        if indent + offset < 0:
            raise ValueError("模型列表缩进格式无效")
        adjusted.append(" " * (indent + offset) + line[indent:])
    return "".join(adjusted)


# 在配置文件中追加模型
def _insert_model_yaml(source: str, values: dict[str, Any]) -> str:
    data = YAML().load(source)
    if data is None:
        data = CommentedMap()
    if not isinstance(data, CommentedMap):
        raise ValueError("配置文件根节点必须是键值结构")

    models_exists = "models" in data
    models = data.get("models")
    if models is None:
        models = CommentedSeq()
    if not isinstance(models, CommentedSeq):
        raise ValueError("模型列表格式无效")
    if any(
        isinstance(model, CommentedMap) and model.get("model_name") == values["model_name"]
        for model in models
    ):
        raise FileExistsError("同名模型已存在")

    newline = "\r\n" if "\r\n" in source else "\n"
    lines = source.splitlines(keepends=True)
    wrapper = CommentedMap({"models": CommentedSeq([CommentedMap(values)])})
    rendered = render_yaml_fragment(wrapper, newline)
    fragment = "".join(rendered.splitlines(keepends=True)[1:])

    if not models_exists:
        prefix = source if not source or source.endswith("\n") else source + newline
        updated = prefix + "models:" + newline + fragment
    else:
        position = data.lc.key("models")
        if position is None:
            raise ValueError("模型列表格式暂不支持合并键")
        header, header_indent = position
        if not models:
            header_line = lines[header]
            content = header_line.rstrip("\r\n")
            match = re.fullmatch(
                r'''(\s*(?:models|'models'|"models")\s*:)[ \t]*(?:\[\]|null|~)?([ \t]*(?:#.*)?)''',
                content,
            )
            if match is None:
                raise ValueError("模型列表格式暂不支持行内写法")
            lines[header] = match.group(1) + match.group(2) + newline
            updated = "".join(lines[: header + 1]) + fragment + "".join(lines[header + 1 :])
        else:
            last = models.lc.item(len(models) - 1)
            if last is None:
                raise ValueError("模型列表格式暂不支持合并键")
            start, _ = last
            item_indent = len(lines[start]) - len(lines[start].lstrip(" "))
            if start <= header or item_indent < header_indent or not lines[start].lstrip().startswith("-"):
                raise ValueError("模型列表格式暂不支持行内写法")
            insert_at = yaml_block_end(lines, start, item_indent)
            fragment = _indent_model_fragment(fragment, item_indent - 2)
            prefix = "".join(lines[:insert_at])
            if prefix and not prefix.endswith("\n"):
                prefix += newline
            updated = prefix + fragment + "".join(lines[insert_at:])

    if source and not source.endswith("\n") and updated.endswith(newline):
        updated = updated[: -len(newline)]
    expected = YAML(typ="safe").load(source) or {}
    if expected.get("models") is None:
        expected["models"] = []
    expected["models"].append(values)
    if YAML(typ="safe").load(updated) != expected:
        raise ValueError("新增模型后的配置校验失败")
    return updated


# 保存新增模型并刷新配置
def create_model_config(values: dict[str, Any]) -> ModelConfigInfo:
    get_app_config()
    prepared = _prepare_model_values(values)
    edit_yaml_text(
        AppConfig.resolve_config_path(),
        lambda source: _insert_model_yaml(source, prepared),
    )
    reload_app_config()
    return next(model for model in list_model_configs() if model.model_name == prepared["model_name"])


# 局部修改指定模型字段
def _edit_model_yaml(source: str, name: str, changes: dict[str, Any]) -> str:
    data = YAML().load(source)
    models = data.get("models") if isinstance(data, CommentedMap) else None
    if not isinstance(models, CommentedSeq):
        raise LookupError("模型不存在")
    matches = [
        index
        for index, item in enumerate(models)
        if isinstance(item, CommentedMap) and item.get("model_name") == name
    ]
    if not matches:
        raise LookupError("模型不存在")
    if len(matches) != 1:
        raise ValueError("模型名称重复，无法确定要修改的配置")

    index = matches[0]
    model = models[index]
    lines = source.splitlines(keepends=True)
    header_position = data.lc.key("models")
    item_position = models.lc.item(index)
    name_position = model.lc.key("model_name")
    if header_position is None or item_position is None or name_position is None:
        raise ValueError("模型列表格式暂不支持合并键")
    header, header_indent = header_position
    start, _ = item_position
    item_indent = len(lines[start]) - len(lines[start].lstrip(" "))
    if start <= header or item_indent < header_indent or not lines[start].lstrip().startswith("-"):
        raise ValueError("模型列表格式暂不支持行内写法")

    original_keys = set(model)
    candidate = deepcopy(model)
    changed_fields: list[str] = []
    for field, value in changes.items():
        if field in original_keys and model[field] == value:
            continue
        if field not in original_keys and value is None:
            continue
        changed_fields.append(field)
        if value is None:
            candidate.pop(field, None)
        else:
            candidate[field] = value
    if not changed_fields:
        return source

    ModelConfig.model_validate(AppConfig.resolve_env_variables(candidate))
    newline = "\r\n" if lines[start].endswith("\r\n") else "\n"
    wrapper = CommentedMap({"models": CommentedSeq([candidate])})
    rendered = render_yaml_fragment(wrapper, newline)
    rendered_lines = rendered.splitlines(keepends=True)
    rendered_model = YAML().load(rendered)["models"][0]
    first_field = next((field for field in model if field != "model_name"), "model_name")
    first_position = model.lc.key(first_field)
    if first_position is None:
        raise ValueError("模型字段格式暂不支持合并键")
    new_field_indent = first_position[1]

    patches: list[tuple[int, int, str]] = []
    additions: list[str] = []
    for field in changed_fields:
        fragment = ""
        if field in candidate:
            rendered_position = rendered_model.lc.key(field)
            if rendered_position is None:
                raise ValueError("模型字段格式暂不支持合并键")
            rendered_start, rendered_indent = rendered_position
            rendered_end = yaml_block_end(rendered_lines, rendered_start, rendered_indent)
            fragment = "".join(rendered_lines[rendered_start:rendered_end])
        if field in original_keys:
            original_position = model.lc.key(field)
            if original_position is None:
                raise ValueError("模型字段格式暂不支持合并键")
            field_start, field_indent = original_position
            if field_start <= start:
                raise ValueError("模型字段格式暂不支持行内写法")
            field_end = yaml_block_end(lines, field_start, field_indent)
            if fragment:
                fragment = _indent_model_fragment(fragment, field_indent - rendered_indent)
            if field_end == len(lines) and not source.endswith("\n"):
                fragment = fragment.rstrip("\r\n")
            patches.append((field_start, field_end, fragment))
        else:
            additions.append(_indent_model_fragment(fragment, new_field_indent - rendered_indent))

    if additions:
        insert_at = yaml_block_end(lines, start, item_indent)
        addition = "".join(additions)
        if insert_at and not lines[insert_at - 1].endswith("\n"):
            addition = newline + addition
        if insert_at == len(lines) and not source.endswith("\n"):
            addition = addition.rstrip("\r\n")
        patches.append((insert_at, insert_at, addition))

    for field_start, field_end, fragment in sorted(patches, key=lambda item: item[0], reverse=True):
        lines[field_start:field_end] = [fragment]
    updated = "".join(lines)
    expected = YAML(typ="safe").load(source)
    expected_model = expected["models"][index]
    for field, value in changes.items():
        if value is None:
            expected_model.pop(field, None)
        else:
            expected_model[field] = value
    try:
        actual = YAML(typ="safe").load(updated)
    except YAMLError as error:
        raise ValueError("修改模型后的配置格式无效") from error
    if actual != expected:
        raise ValueError("修改模型后的配置校验失败")
    return updated


# 保存模型配置修改
def update_model_config(name: str, changes: dict[str, Any]) -> ModelConfigInfo:
    get_app_config()
    prepared = _prepare_model_changes(changes)
    changed = False

    def edit(source: str) -> str:
        nonlocal changed
        updated = _edit_model_yaml(source, name, prepared)
        changed = updated != source
        return updated

    edit_yaml_text(AppConfig.resolve_config_path(), edit)
    if changed:
        reload_app_config()
    return next(model for model in list_model_configs() if model.model_name == name)


# 将指定模型的配置块移到列表首位
def _set_default_model_yaml(source: str, name: str) -> str:
    data = YAML().load(source)
    models = data.get("models") if isinstance(data, CommentedMap) else None
    if not isinstance(models, CommentedSeq):
        raise LookupError("模型不存在")

    matches = [
        index
        for index, model in enumerate(models)
        if isinstance(model, CommentedMap) and model.get("model_name") == name
    ]
    if not matches:
        raise LookupError("模型不存在")
    if len(matches) != 1:
        raise ValueError("模型名称重复，无法确定默认模型")
    index = matches[0]
    if index == 0:
        return source

    lines = source.splitlines(keepends=True)
    header_position = data.lc.key("models")
    if header_position is None:
        raise ValueError("模型列表格式暂不支持合并键")
    header, header_indent = header_position
    item_ends: list[int] = []
    for item in range(len(models)):
        position = models.lc.item(item)
        if position is None:
            raise ValueError("模型列表格式暂不支持合并键")
        start, _ = position
        item_indent = len(lines[start]) - len(lines[start].lstrip(" "))
        if start <= header or item_indent < header_indent or not lines[start].lstrip().startswith("-"):
            raise ValueError("模型列表格式暂不支持行内写法")
        item_ends.append(yaml_block_end(lines, start, item_indent))

    segment_starts = [header + 1, *item_ends[:-1]]
    segments = ["".join(lines[start:end]) for start, end in zip(segment_starts, item_ends)]
    reordered = [segments[index], *segments[:index], *segments[index + 1 :]]
    suffix = "".join(lines[item_ends[-1] :])
    newline = "\r\n" if "\r\n" in source else "\n"
    for segment_index in range(len(reordered) - 1):
        if not reordered[segment_index].endswith("\n"):
            reordered[segment_index] += newline
    if not suffix and not source.endswith("\n"):
        reordered[-1] = reordered[-1].removesuffix(newline)
    updated = "".join(lines[: header + 1]) + "".join(reordered) + suffix

    expected = YAML(typ="safe").load(source)
    expected_models = expected["models"]
    expected_models.insert(0, expected_models.pop(index))
    try:
        actual = YAML(typ="safe").load(updated)
    except YAMLError as error:
        raise ValueError("调整模型顺序后配置格式无效") from error
    if actual != expected:
        raise ValueError("设置默认模型后的配置校验失败")
    return updated


# 保存默认模型并刷新配置
def set_default_model_config(name: str) -> list[ModelConfigInfo]:
    get_app_config()
    changed = False

    def edit(source: str) -> str:
        nonlocal changed
        updated = _set_default_model_yaml(source, name)
        changed = updated != source
        return updated

    edit_yaml_text(AppConfig.resolve_config_path(), edit)
    if changed:
        reload_app_config()
    return list_model_configs()


# 删除指定模型的 YAML 配置块
def _remove_model_yaml(source: str, name: str) -> str:
    data = YAML().load(source)
    models = data.get("models") if isinstance(data, CommentedMap) else None
    if not isinstance(models, CommentedSeq):
        raise LookupError("模型不存在")

    matches = [
        index
        for index, model in enumerate(models)
        if isinstance(model, CommentedMap) and model.get("model_name") == name
    ]
    if not matches:
        raise LookupError("模型不存在")
    if len(matches) != 1:
        raise ValueError("模型名称重复，无法确定要删除的配置")

    index = matches[0]
    lines = source.splitlines(keepends=True)
    header, header_indent = data.lc.key("models")
    position = models.lc.item(index)
    if position is None:
        raise ValueError("模型列表格式暂不支持合并键")
    start, _ = position
    item_indent = len(lines[start]) - len(lines[start].lstrip(" "))
    if start <= header or item_indent <= header_indent or not lines[start].lstrip().startswith("-"):
        raise ValueError("模型列表格式暂不支持行内写法")
    end = yaml_block_end(lines, start, item_indent)

    if len(models) == 1:
        header_line = lines[header]
        content = header_line.rstrip("\r\n")
        newline = header_line[len(content) :]
        match = re.fullmatch(r'''(\s*(?:models|'models'|"models")\s*:)([ \t]*)(#.*)?''', content)
        if match is None:
            raise ValueError("模型列表格式暂不支持行内写法")
        comment = match.group(3) or ""
        spacing = match.group(2) if comment else ""
        lines[header] = f"{match.group(1)} []{spacing}{comment}{newline}"

    updated = "".join(lines[:start] + lines[end:])
    expected = YAML(typ="safe").load(source)
    expected["models"].pop(index)
    if YAML(typ="safe").load(updated) != expected:
        raise ValueError("删除模型后的配置校验失败")
    return updated


# 删除模型并刷新配置
def delete_model_config(name: str) -> None:
    edit_yaml_text(
        AppConfig.resolve_config_path(),
        lambda source: _remove_model_yaml(source, name),
    )
    reload_app_config()
