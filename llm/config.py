from dataclasses import dataclass

from injector import inject
from typing import Optional, List, Dict, Any, Literal, NamedTuple
import os
import json, re

ConfigSourceType = Literal["env", "json", "app", "default"]
ConfigValueType = Literal["str", "int", "float", "bool", "list", "enum", "path"]


class ConfigSourceValue(NamedTuple):
    source: ConfigSourceType
    value: Any


@dataclass
class ConfigItem:
    name: str
    value: Any
    type: ConfigValueType
    sources: List[ConfigSourceValue]


class ConfigSource:
    _bool_str_map: Dict[str, bool] = {
        "true": True,
        "false": False,
        "yes": True,
        "no": False,
        "1": True,
        "0": False,
    }
    _null_str_set = set(["null", "none", "nil"])

    _path_app_base_ref: str = "${AppBaseDir}"
    _path_module_base_ref: str = "${ModuleBaseDir}"

    def __init__(
            self,
            config_file_path: Optional[str] = None,
            config: Optional[Dict[str, Any]] = None,
            base_path: Optional[str] = None,
    ):
        self.module_base_path = os.path.realpath(
            os.path.join(os.path.dirname(__file__), ".."),
        )
        self.base_path = os.path.realpath(".") if base_path is None else os.path.realpath(base_path)

        self.config: Dict[str, ConfigItem] = {}
        self.config_file_path = config_file_path
        self.in_memory_store = config
        if self.config_file_path is not None:
            self.json_file_store = self._load_config_from_json(self.config_file_path)
        else:
            self.json_file_store = {}

    def _load_config_from_json(self, config_file_path: str) -> Dict[str, Any]:
        self.config_file_path = config_file_path
        assert os.path.exists(
            self.config_file_path,
        ), f"Config file {config_file_path} does not exist"
        try:
            with open(self.config_file_path, "r", encoding="utf-8") as f:
                self.json_file_store = json.load(f)
                return self.json_file_store
        except Exception as e:
            raise e

    def _get_config_value(
            self,
            var_name: str,
            var_type: ConfigValueType,
            default_value: Optional[Any] = None,
    ) -> Optional[Any]:
        self.set_config_value(var_name, var_type, default_value, "default")

        if self.in_memory_store is not None:
            val = self.in_memory_store.get(var_name, None)
            if val is not None:
                return val
        # env var has the format of upper case with dot replaced by underscore
        # e.g., llm.api_base -> LLM_API_BASE
        val = os.environ.get(var_name.upper().replace(".", "_"), None)
        if val is not None:
            if val.lower() in ConfigSource._null_str_set:
                return None
            else:
                return val

        if var_name in self.json_file_store.keys():
            return self.json_file_store.get(var_name, default_value)

        if default_value is not None:
            return default_value

        raise ValueError(f"Config value {var_name} is not found")

    def set_config_value(
            self,
            var_name: str,
            var_type: ConfigValueType,
            value: Optional[Any],
            source: ConfigSourceType = "app",
    ):
        if not (var_name in self.config.keys()):
            self.config[var_name] = ConfigItem(
                name=var_name,
                value=value,
                type=var_type,
                sources=[ConfigSourceValue(source=source, value=value)],
            )
        else:
            self.config[var_name].value = value
            new_sources = [s for s in self.config[var_name].sources if s.source != source]
            new_sources.append(ConfigSourceValue(source=source, value=value))
            self.config[var_name].sources = new_sources

    def get_bool(
            self,
            var_name: str,
            default_value: Optional[bool] = None,
    ) -> bool:
        val = self._get_config_value(var_name, "bool", default_value)
        if isinstance(val, bool):
            return val
        elif str(val).lower() in ConfigSource._bool_str_map.keys():
            return ConfigSource._bool_str_map[str(val).lower()]
        else:
            raise ValueError(
                f"Invalid boolean config value {val}, "
                f"only support transforming {ConfigSource._bool_str_map.keys()}",
            )

    def get_str(self, var_name: str, default_value: Optional[str] = None) -> str:
        val = self._get_config_value(var_name, "str", default_value)

        if val is None and default_value is None:
            raise ValueError(f"Invalid string config value {val}")

        return str(val)

    def get_enum(
            self,
            key: str,
            options: List[str],
            default: Optional[str] = None,
    ) -> str:
        val = self._get_config_value(key, "enum", default)
        if val not in options:
            raise ValueError(f"Invalid enum config value {val}, options are {options}")
        return val

    def get_list(self, key: str, default: Optional[List[Any]] = None) -> List[str]:
        val = self._get_config_value(key, "list", default)
        if isinstance(val, list):
            return val
        elif isinstance(val, str):
            return re.split(r"\s*,\s*", val)
        elif val is None:
            return []
        else:
            raise ValueError(f"Invalid list config value {val}")

    def get_float(
            self,
            var_name: str,
            default_value: Optional[float] = None,
    ) -> float:
        val = self._get_config_value(var_name, "int", default_value)
        if isinstance(val, float):
            return val
        if isinstance(val, int):
            return float(val)
        else:
            try:
                any_val: Any = val
                float_number = float(any_val)
                return float_number
            except ValueError:
                raise ValueError(
                    f"Invalid digit config value {val}, " f"only support transforming to int or float",
                )

    def get_int(
            self,
            var_name: str,
            default_value: Optional[int] = None,
    ) -> int:
        val = self._get_config_value(var_name, "int", default_value)
        if isinstance(val, int):
            return val
        if isinstance(val, float):
            return int(val)
        else:
            try:
                any_val: Any = val
                int_number = int(any_val)
                return int_number
            except ValueError:
                raise ValueError(
                    f"Invalid digit config value {val}, " f"only support transforming to int or float",
                )

    def get_path(
            self,
            var_name: str,
            default_value: Optional[str] = None,
    ) -> str:
        if default_value is not None:
            default_value = self.normalize_path_val_config(default_value)

        val = self._get_config_value(var_name, "path", default_value)
        if val is None and default_value is None:
            raise ValueError(f"Invalid path config value {val}")
        return self.decode_path_val_config(str(val))

    def normalize_path_val_config(self, path_val: str) -> str:
        if path_val.startswith(self.app_base_path):
            path_val = path_val.replace(self.app_base_path, self._path_app_base_ref, 1)
        if path_val.startswith(self.module_base_path):
            path_val = path_val.replace(
                self.module_base_path,
                self._path_module_base_ref,
                1,
            )
        # if path is under user's home, normalize to relative to user
        user_home = os.path.expanduser("~")
        if path_val.startswith(user_home):
            path_val = path_val.replace(user_home, "~", 1)

        # normalize path separator
        path_val = path_val.replace(os.path.sep, "/")

        return path_val

    def decode_path_val_config(self, path_config: str) -> str:
        # normalize path separator
        path_config = path_config.replace("/", os.path.sep)

        if path_config.startswith(self._path_app_base_ref):
            path_config = path_config.replace(
                self._path_app_base_ref,
                self.app_base_path,
                1,
            )
        if path_config.startswith(self._path_module_base_ref):
            path_config = path_config.replace(
                self._path_module_base_ref,
                self.module_base_path,
                1,
            )

        if path_config.startswith("~"):
            path_config = os.path.expanduser(path_config)
        return path_config


class ModuleConfig(object):
    @inject
    def __init__(self, src: ConfigSource) -> None:
        self.src: ConfigSource = src
        self.name: str = ""
        self._configure()

    def _set_name(self, name: str) -> None:
        self.name = name

    def _config_key(self, key: str) -> str:
        return f"{self.name}.{key}" if self.name != "" else key

    def _configure(self) -> None:
        pass

    def _get_str(self, key: str, default: Optional[str]) -> str:
        return self.src.get_str(self._config_key(key), default)

    def _get_enum(self, key: str, options: List[str], default: Optional[str]) -> str:
        return self.src.get_enum(self._config_key(key), options, default)

    def _get_bool(self, key: str, default: Optional[bool]) -> bool:
        return self.src.get_bool(self._config_key(key), default)

    def _get_list(self, key: str, default: Optional[List[str]]) -> List[str]:
        return self.src.get_list(self._config_key(key), default)

    def _get_int(self, key: str, default: Optional[int]) -> int:
        return self.src.get_int(self._config_key(key), default)

    def _get_float(self, key: str, default: Optional[float]) -> float:
        return self.src.get_float(self._config_key(key), default)

    def _get_path(self, key: str, default: Optional[str]) -> str:
        return self.src.get_path(self._config_key(key), default)


class LLMModuleConfig(ModuleConfig):
    def _configure(self) -> None:
        self._set_name("llm")
        self.api_type = self._get_enum(
            "api_type",
            ["openai", "azure", "azure_ad"],
            "openai",
        )
        self.api_base = self._get_str("api_base", "https://api.openai.com/v1")
        self.api_key = self._get_str(
            "api_key",
            None if self.api_type != "azure_ad" else "",
        )

        self.model = self._get_str("model", "gpt-4")
        self.backup_model = self._get_str("backup_model", self.model)

        self.api_version = self._get_str("api_version", "2023-07-01-preview")

        is_azure_ad_login = self.api_type == "azure_ad"
        self.aad_auth_mode = self._get_enum(
            "aad_auth_mode",
            ["device_login", "aad_app"],
            None if is_azure_ad_login else "device_login",
        )

        is_app_login = is_azure_ad_login and self.aad_auth_mode == "aad_app"
        self.aad_tenant_id = self._get_str(
            "aad_tenant_id",
            None if is_app_login else "common",
        )
        self.aad_api_resource = self._get_str(
            "aad_api_resource",
            None if is_app_login else "https://cognitiveservices.azure.com/",
        )
        self.aad_api_scope = self._get_str(
            "aad_api_scope",
            None if is_app_login else ".default",
        )
        self.aad_client_id = self._get_str(
            "aad_client_id",
            None if is_app_login else "",
        )
        self.aad_client_secret = self._get_str(
            "aad_client_secret",
            None if is_app_login else "",
        )
        self.aad_use_token_cache = self._get_bool("aad_use_token_cache", True)
        self.aad_token_cache_path = self._get_str(
            "aad_token_cache_path",
            "cache/token_cache.bin",
        )
        self.aad_token_cache_full_path = os.path.join(
            self.src.base_path,
            self.aad_token_cache_path,
        )
        self.response_format = self._get_enum(
            "response_format",
            options=["json_object", "text", None],
            default="text",
        )
