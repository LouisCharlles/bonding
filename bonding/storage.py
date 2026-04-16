import mimetypes
import posixpath
import uuid
import json
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.parse import quote
from urllib.request import Request, urlopen

from django.conf import settings
from django.core.files.base import ContentFile, File
from django.core.files.storage import FileSystemStorage, Storage
from django.utils.deconstruct import deconstructible


def _clean_base_url(url: str) -> str:
    return url.rstrip("/")


@deconstructible
class SupabaseStorage(Storage):
    def __init__(self, base_url=None, bucket=None, service_role_key=None):
        self.base_url = _clean_base_url(base_url or getattr(settings, "SUPABASE_URL", ""))
        self.bucket = bucket or getattr(settings, "SUPABASE_STORAGE_BUCKET", "")
        self.service_role_key = service_role_key or getattr(settings, "SUPABASE_SERVICE_ROLE_KEY", "")

    @property
    def is_configured(self) -> bool:
        return bool(self.base_url and self.bucket and self.service_role_key)

    def _build_object_url(self, name: str) -> str:
        encoded_name = quote(name.lstrip("/"), safe="/")
        return f"{self.base_url}/storage/v1/object/{self.bucket}/{encoded_name}"

    def _build_public_url(self, name: str) -> str:
        encoded_name = quote(name.lstrip("/"), safe="/")
        return f"{self.base_url}/storage/v1/object/public/{self.bucket}/{encoded_name}"

    def _request(self, method: str, url: str, data: bytes | None = None, content_type: str | None = None):
        headers = {
            "apikey": self.service_role_key,
            "Authorization": f"Bearer {self.service_role_key}",
        }
        if content_type:
            headers["Content-Type"] = content_type
        if method in {"POST", "PUT"}:
            headers["x-upsert"] = "true"

        request = Request(url, data=data, headers=headers, method=method)
        try:
            return urlopen(request)
        except HTTPError as exc:
            details = exc.read().decode("utf-8", errors="replace")
            raise RuntimeError(
                f"Supabase Storage {method} {url} falhou com status {exc.code}: {details}"
            ) from exc

    def _open(self, name, mode="rb"):
        if not self.is_configured:
            raise FileNotFoundError(name)

        try:
            with self._request("GET", self._build_object_url(name)) as response:
                return File(ContentFile(response.read()), name=name)
        except (HTTPError, URLError) as exc:
            raise FileNotFoundError(name) from exc

    def _save(self, name, content):
        name = name.replace('\\', '/')
        if not self.is_configured:
            raise RuntimeError("Supabase Storage não está configurado.")

        directory, filename = posixpath.split(name)
        original_extension = Path(filename).suffix.lower()
        content_type = getattr(content, "content_type", None) or mimetypes.guess_type(filename)[0] or "application/octet-stream"
        guessed_extension = mimetypes.guess_extension(content_type.split(";")[0]) or ""
        extension = original_extension or guessed_extension
        unique_name = f"{uuid.uuid4().hex}{extension}"
        final_name = posixpath.join(directory, unique_name) if directory else unique_name
        file_bytes = content.read()

        self._request(
            "PUT",
            self._build_object_url(final_name),
            data=file_bytes,
            content_type=content_type,
        )
        return final_name

    def get_available_name(self, name, max_length=None):
        return name

    def delete(self, name):
        if not self.is_configured or not name:
            return

        try:
            self._request(
                "DELETE",
                f"{self.base_url}/storage/v1/object/{self.bucket}",
                data=json.dumps({"prefixes": [name]}).encode("utf-8"),
                content_type="application/json",
            )
        except HTTPError as exc:
            if exc.code != 404:
                raise

    def exists(self, name):
        return False

    def url(self, name):
        return self._build_public_url(name)

    def size(self, name):
        if not self.is_configured or not name:
            return 0

        try:
            with self._request("HEAD", self._build_object_url(name)) as response:
                return int(response.headers.get("Content-Length", "0"))
        except (HTTPError, URLError, ValueError):
            return 0


def get_photo_storage():
    supabase_storage = SupabaseStorage()
    if supabase_storage.is_configured:
        return supabase_storage
    return FileSystemStorage()
