import os
from typing import Any, Callable, Generator, Iterator, List, Literal, Optional, TypeVar, Union, overload, Dict

import openai
from injector import inject
from openai import AzureOpenAI, OpenAI
from langchain.embeddings import OpenAIEmbeddings, AzureOpenAIEmbeddings
from llm.config import LLMModuleConfig, ModuleConfig, ConfigSource
from llm import PROJECT_DIR

ChatMessageRoleType = Literal["system", "user", "assistant"]
ChatMessageType = Dict[Literal["role", "name", "content"], str]


def format_chat_message(
        role: ChatMessageRoleType,
        message: str,
        name: Optional[str] = None,
) -> ChatMessageType:
    msg: ChatMessageType = {
        "role": role,
        "content": message,
    }
    if name is not None:
        msg["name"] = name
    return msg


DEFAULT_STOP_TOKEN: List[str] = ["<EOS>"]

# TODO: retry logic

_FuncType = TypeVar("_FuncType", bound=Callable[..., Any])


class LLMApi(object):
    import torch
    EMBEDDING_DEVICE = "cuda" if torch.cuda.is_available() else "mps" if torch.backends.mps.is_available() else "cpu"

    @inject
    def __init__(self, config: LLMModuleConfig):
        self.config = config

    @staticmethod
    def create_api(config_file: str = None):
        """
        Factory method to create api from config file
        :param config_file: config_file path
        :return LLMApi specified by config file
        """
        if config_file is None:
            config_file = os.path.join(PROJECT_DIR, 'llm', 'chat_config.json')
        if not os.path.exists(config_file):
            raise Exception(f"{config_file} does not exists")
        config = LLMModuleConfig(ConfigSource(config_file))
        return LLMApi(config)

    def create_openai_embeddings(self):
        api_type = self.config.api_type
        if api_type == "azure":
            return AzureOpenAIEmbeddings(azure_endpoint=self.config.api_base, openai_api_type=api_type,
                                         openai_api_key=self.config.api_key, openai_api_version=self.config.api_version,
                                         )
        elif api_type == "azure_ad":
            return AzureOpenAIEmbeddings(azure_endpoint=self.config.api_base, openai_api_type=api_type,
                                         openai_api_key=self._get_aad_token(),
                                         openai_api_version=self.config.api_version,
                                         )
        elif api_type == "openai":
            return OpenAIEmbeddings(openai_api_base=self.config.api_base, openai_api_type=api_type,
                                    openai_api_key=self.config.api_key, openai_api_version=self.config.api_version
                                    )
        else:
            raise Exception(f"do not support llm api type:{api_type}")

    def _get_aad_token(self) -> str:
        # TODO: migrate to azure-idnetity module
        try:
            import msal
        except ImportError:
            raise Exception("AAD authentication requires msal module to be installed, please run `pip install msal`")

        config = self.config

        cache = msal.SerializableTokenCache()

        token_cache_file: Optional[str] = None
        if config.aad_use_token_cache:
            token_cache_file = config.aad_token_cache_full_path
            if not os.path.exists(token_cache_file):
                os.makedirs(os.path.dirname(token_cache_file), exist_ok=True)
            if os.path.exists(token_cache_file):
                with open(token_cache_file, "r") as cache_file:
                    cache.deserialize(cache_file.read())

        def save_cache():
            if token_cache_file is not None and config.aad_use_token_cache:
                with open(token_cache_file, "w") as cache_file:
                    cache_file.write(cache.serialize())

        authority = "https://login.microsoftonline.com/" + config.aad_tenant_id
        api_resource = config.aad_api_resource
        api_scope = config.aad_api_scope
        auth_mode = config.aad_auth_mode

        if auth_mode == "aad_app":
            app = msal.ConfidentialClientApplication(
                client_id=config.aad_client_id,
                client_credential=config.aad_client_secret,
                authority=authority,
                token_cache=cache,
            )
            result = app.acquire_token_for_client(
                scopes=[
                    api_resource + "/" + api_scope,
                ],
            )
            if "access_token" in result:
                return result["access_token"]
            else:
                raise Exception(
                    "Authentication failed for acquiring AAD token for application login: " + str(result),
                )

        scopes = [
            api_resource + "/" + api_scope,
        ]
        app = msal.PublicClientApplication(
            "feb7b661-cac7-44a8-8dc1-163b63c23df2",  # default id in Azure Identity module
            authority=authority,
            token_cache=cache,
        )
        result = None
        try:
            account = app.get_accounts()[0]
            result = app.acquire_token_silent(scopes, account=account)
            if result is not None and "access_token" in result:
                save_cache()
                return result["access_token"]
            result = None
        except Exception:
            pass

        try:
            account = cache.find(cache.CredentialType.ACCOUNT)[0]
            refresh_token = cache.find(
                cache.CredentialType.REFRESH_TOKEN,
                query={
                    "home_account_id": account["home_account_id"],
                },
            )[0]
            result = app.acquire_token_by_refresh_token(
                refresh_token["secret"],
                scopes=scopes,
            )
            if result is not None and "access_token" in result:
                save_cache()
                return result["access_token"]
            result = None
        except Exception:
            pass

        if result is None:
            print("no token available from cache, acquiring token from AAD")
            # The pattern to acquire a token looks like this.
            flow = app.initiate_device_flow(scopes=scopes)
            print(flow["message"])
            result = app.acquire_token_by_device_flow(flow=flow)
            if result is not None and "access_token" in result:
                save_cache()
                return result["access_token"]
            else:
                print(result.get("error"))
                print(result.get("error_description"))
                raise Exception(
                    "Authentication failed for acquiring AAD token for AAD auth",
                )

    def chat_completion_stream(self, prompt: List[ChatMessageType]) -> Iterator[str]:
        message = ""
        try:
            response = self.chat_completion(prompt, stream=True)
            for chunk in response:
                message += chunk["content"]
                yield chunk["content"]
        except Exception as e:
            raise e

    @overload
    def chat_completion(
            self,
            messages: List[ChatMessageType],
            engine: str = ...,
            temperature: float = ...,
            max_tokens: int = ...,
            top_p: float = ...,
            frequency_penalty: float = ...,
            presence_penalty: float = ...,
            stop: Union[str, List[str]] = ...,
            stream: Literal[False] = ...,
            backup_engine: str = ...,
            use_backup_engine: bool = ...,
            response_format: str = ...
    ) -> ChatMessageType:
        ...

    @overload
    def chat_completion(
            self,
            messages: List[ChatMessageType],
            engine: str = ...,
            temperature: float = ...,
            max_tokens: int = ...,
            top_p: float = ...,
            frequency_penalty: float = ...,
            presence_penalty: float = ...,
            stop: Union[str, List[str]] = ...,
            stream: Literal[True] = ...,
            backup_engine: str = ...,
            use_backup_engine: bool = ...,
            response_format: str = ...
    ) -> Generator[ChatMessageType, None, None]:
        ...

    def chat_completion(
            self,
            messages: List[ChatMessageType],
            engine: Optional[str] = None,
            temperature: float = 0,
            max_tokens: int = 2048,
            top_p: float = 0,
            frequency_penalty: float = 0,
            presence_penalty: float = 0,
            stop: Union[str, List[str]] = DEFAULT_STOP_TOKEN,
            stream: bool = False,
            backup_engine: Optional[str] = None,
            use_backup_engine: bool = False,
            response_format: str = None
    ) -> Union[ChatMessageType, Generator[ChatMessageType, None, None]]:
        api_type = self.config.api_type
        if api_type == "azure":
            client = AzureOpenAI(
                api_version=self.config.api_version,
                azure_endpoint=self.config.api_base,
                api_key=self.config.api_key,
            )
        elif api_type == "azure_ad":
            client = AzureOpenAI(
                api_version=self.config.api_version,
                azure_endpoint=self.config.api_base,
                api_key=self._get_aad_token(),
            )
        elif api_type == "openai":
            client = OpenAI(
                base_url=self.config.api_base,
                api_key=self.config.api_key,
            )

        engine = self.config.model if engine is None else engine
        backup_engine = self.config.backup_model if backup_engine is None else backup_engine

        def handle_stream_result(res):
            for stream_res in res:
                if not stream_res.choices:
                    continue
                delta = stream_res.choices[0].delta
                yield delta.content

        try:
            if use_backup_engine:
                engine = backup_engine
            response_format = response_format if response_format else self.config.response_format
            res: Any = client.chat.completions.create(
                model=engine,
                messages=messages,
                temperature=temperature,
                max_tokens=max_tokens,
                top_p=top_p,
                frequency_penalty=frequency_penalty,
                presence_penalty=presence_penalty,
                stop=stop,
                stream=stream,
                seed=123456,
                response_format={"type": response_format},
            )
            if stream:
                return handle_stream_result(res)
            else:
                oai_response = res.choices[0].message
                if oai_response is None:
                    raise Exception("OpenAI API returned an empty response")
                response: ChatMessageType = format_chat_message(
                    role=oai_response.role if oai_response.role is not None else "assistant",
                    message=oai_response.content if oai_response.content is not None else "",
                )
                return response

        except openai.APITimeoutError as e:
            # Handle timeout error, e.g. retry or log
            raise Exception(f"OpenAI API request timed out: {e}")
        except openai.APIConnectionError as e:
            # Handle connection error, e.g. check network or log
            raise Exception(f"OpenAI API request failed to connect: {e}")
        except openai.BadRequestError as e:
            # Handle invalid request error, e.g. validate parameters or log
            raise Exception(f"OpenAI API request was invalid: {e}")
        except openai.AuthenticationError as e:
            # Handle authentication error, e.g. check credentials or log
            raise Exception(f"OpenAI API request was not authorized: {e}")
        except openai.PermissionDeniedError as e:
            # Handle permission error, e.g. check scope or log
            raise Exception(f"OpenAI API request was not permitted: {e}")
        except openai.RateLimitError as e:
            # Handle rate limit error, e.g. wait or log
            raise Exception(f"OpenAI API request exceeded rate limit: {e}")
        except openai.APIError as e:
            # Handle API error, e.g. retry or log
            raise Exception(f"OpenAI API returned an API Error: {e}")
