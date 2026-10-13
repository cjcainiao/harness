# 模型配置业务

from ruamel.yaml import YAML
from ruamel.yaml.comments import CommentedMap, CommentedSeq

from app.schemas.config.model import ModelConfigItem
from harness.config.app_config import AppConfig, get_app_config
from harness.config.model_config import ModelConfig
from harness.utils.yaml_util import edit_yaml_text, render_yaml_fragment, yaml_block_end


# 模型配置错误
class ModelConfigManagementError(ValueError):
    def __init__(self, status_code: int, message: str) -> None:
        self.status_code = status_code
        super().__init__(message)


# 获取模型配置列表
def list_model_configs() -> list[ModelConfigItem]:
    items: list[ModelConfigItem] = []
    for model in get_app_config().models:
        settings = model.model_extra or {}
        items.append(
            ModelConfigItem(
                model_name=model.model_name,
                display_name=model.display_name or model.model_name,
                description=model.description,
                provider=model.provider,
                use=model.use,
                base_url_configured=bool(settings.get("base_url")),
                api_key_configured=bool(settings.get("api_key")),
                timeout=settings.get("timeout"),
                max_retries=settings.get("max_retries"),
                max_tokens=settings.get("max_tokens"),
                supports_thinking=model.supports_thinking,
                reasoning_levels=model.reasoning_levels,
                when_thinking_enabled=model.when_thinking_enabled,
                when_thinking_disabled=model.when_thinking_disabled,
                supports_vision=model.supports_vision,
                context_window=model.context_window,
            )
        )
    return items


# 修改模型配置
def update_model_config(model_name: str, model: ModelConfig) -> None:
    config_path = AppConfig.resolve_config_path()

    # 只替换目标模型配置块
    def update_model(source: str) -> str:
        yaml = YAML()
        data = yaml.load(source)
        models = data.get("models") or []
        matches = [index for index, item in enumerate(models) if item.get("model_name") == model_name]
        if not matches:
            raise ModelConfigManagementError(404, f"模型不存在：{model_name}")
        if len(matches) > 1:
            raise ModelConfigManagementError(409, f"模型名称重复：{model_name}")
        if model.model_name != model_name and any(
            item.get("model_name") == model.model_name for item in models
        ):
            raise ModelConfigManagementError(409, f"模型已存在：{model.model_name}")
        if not isinstance(models, CommentedSeq) or models.fa.flow_style():
            raise ModelConfigManagementError(400, "模型配置必须使用块列表格式")

        index = matches[0]
        target = models[index]
        target.update(model.model_dump(exclude_none=True, exclude_unset=True))
        newline = "\r\n" if "\r\n" in source else "\n"
        fragment = render_yaml_fragment(CommentedMap({"models": CommentedSeq([target])}), newline)
        replacement = "".join(fragment.splitlines(keepends=True)[1:])
        lines = source.splitlines(keepends=True)
        start = models.lc.item(index)[0]
        end = yaml_block_end(lines, start, 2)
        updated = "".join(lines[:start]) + replacement + "".join(lines[end:])
        if yaml.load(updated) != data:
            raise RuntimeError("修改模型后的配置校验失败")
        return updated

    edit_yaml_text(config_path, update_model)


# 新增模型配置
def create_model_config(model: ModelConfig) -> None:
    config_path = AppConfig.resolve_config_path()

    # 在模型列表末尾插入新配置块
    def add_model(source: str) -> str:
        yaml = YAML()
        data = yaml.load(source)
        models = data.get("models") or []
        if any(item.get("model_name") == model.model_name for item in models):
            raise ModelConfigManagementError(409, f"模型已存在：{model.model_name}")
        if not isinstance(models, CommentedSeq) or not models or models.fa.flow_style():
            raise ModelConfigManagementError(400, "模型配置必须使用非空块列表格式")

        item = CommentedMap(model.model_dump(exclude_none=True))
        newline = "\r\n" if "\r\n" in source else "\n"
        fragment = render_yaml_fragment(CommentedMap({"models": CommentedSeq([item])}), newline)
        addition = "".join(fragment.splitlines(keepends=True)[1:])
        lines = source.splitlines(keepends=True)
        last_start = models.lc.item(len(models) - 1)[0]
        insert_at = yaml_block_end(lines, last_start, 2)
        prefix = "" if insert_at and not lines[insert_at - 1].strip() else newline
        updated = "".join(lines[:insert_at]) + prefix + addition + "".join(lines[insert_at:])
        models.append(item)
        if yaml.load(updated) != data:
            raise RuntimeError("新增模型后的配置校验失败")
        return updated

    edit_yaml_text(config_path, add_model)


# 删除模型配置
def delete_model_config(model_name: str) -> None:
    config_path = AppConfig.resolve_config_path()

    # 只移除目标模型的原始文本块
    def remove_model(source: str) -> str:
        yaml = YAML()
        data = yaml.load(source)
        models = data.get("models") or []
        matches = [
            index for index, item in enumerate(models) if item.get("model_name") == model_name
        ]
        if not matches:
            raise ModelConfigManagementError(404, f"模型不存在：{model_name}")
        if len(matches) > 1:
            raise ModelConfigManagementError(409, f"模型名称重复：{model_name}")
        if len(models) == 1:
            raise ModelConfigManagementError(409, "至少保留一个模型")
        if not isinstance(models, CommentedSeq) or models.fa.flow_style():
            raise ModelConfigManagementError(400, "模型配置必须使用块列表格式")

        index = matches[0]
        lines = source.splitlines(keepends=True)
        item_line = models.lc.item(index)[0]
        start = item_line
        if index > 0:
            previous_line = models.lc.item(index - 1)[0]
            while start > previous_line + 1:
                previous = lines[start - 1]
                if previous.strip() and not previous.lstrip().startswith("#"):
                    break
                start -= 1

        if index < len(models) - 1:
            next_item_line = models.lc.item(index + 1)[0]
            next_header_line = next_item_line
            while next_header_line > item_line + 1:
                previous = lines[next_header_line - 1]
                if previous.strip() and not previous.lstrip().startswith("#"):
                    break
                next_header_line -= 1
            if index == 0:
                end = next(
                    (
                        line_number
                        for line_number in range(next_header_line, next_item_line)
                        if lines[line_number].lstrip().startswith("#")
                    ),
                    next_item_line,
                )
            else:
                end = next_header_line
        else:
            end = len(lines)
            for line_number in range(item_line + 1, len(lines)):
                line = lines[line_number]
                if line.strip() and not line[0].isspace():
                    end = line_number
                    while end > item_line:
                        previous = lines[end - 1]
                        if previous.strip() and not previous.lstrip().startswith("#"):
                            break
                        end -= 1
                    break

        updated = "".join(lines[:start] + lines[end:])
        models.pop(index)
        if yaml.load(updated) != data:
            raise RuntimeError("删除模型后的配置校验失败")
        return updated

    edit_yaml_text(config_path, remove_model)
