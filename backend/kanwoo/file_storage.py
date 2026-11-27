import os
from abc import abstractmethod, ABC
import boto3
from botocore.exceptions import ClientError
from botocore.config import Config


from kanwoo.entities import File

CHAPTER_OBJECT_PREFIX = "chapters/"
OPTIMIZED_CHAPTER_OBJECT_PREFIX = f"{CHAPTER_OBJECT_PREFIX}optimized/"
LEGACY_CHAPTER_OBJECT_PREFIX = "chapter-originals/"

class FileExistException(Exception):
    pass

class FileStorageMixin(ABC):
    
    @abstractmethod
    def __init__(self, app):
        pass
    
    @abstractmethod
    def init_app(self, app):
        pass

    @abstractmethod
    def save(self, file, key):
        pass

    @abstractmethod
    def delete(self, key):
        pass

    @abstractmethod
    def exists(self, key):
        pass

    @abstractmethod
    def get_url(self, key):
        pass

    @abstractmethod
    def get_upload_url(self, key):
        pass

class LocalStorage(FileStorageMixin):
    def __init__(self, app=None):
        self.app = app
        self.upload_dir = None
        self.cdn_url = None

        if app is not None:
            self.init_app(app)

    def init_app(self, app):
        self.app = app
        self.upload_dir = app.config['UPLOAD_DIR']
        self.cdn_url = app.config['CDN_URL']

    def save(self, file: File, key: str):
        folders_path, _ = key.rsplit("/", maxsplit=1)

        folder_path = os.path.join(self.upload_dir, folders_path)
        file_path = os.path.join(self.upload_dir, key)

        if os.path.exists(file_path):
            raise FileExistException(f"File with path '{key}' already exists.")
        
        if not os.path.exists(folder_path):
            os.makedirs(os.path.join(self.upload_dir, folders_path))

        with open(file_path, "wb") as f:
            f.write(file.bytes)

    def delete(self, key: str):
        file_path = os.path.join(self.upload_dir, key)
        if os.path.exists(file_path):
            os.remove(file_path)
            print(file_path)

    def exists(self, key: str):
        return os.path.exists(os.path.join(self.upload_dir, key))

    def get_url(self, key: str):
        return os.path.join(self.cdn_url, key)

    def get_upload_url(self, key: str):
        return os.path.join(self.cdn_url, key)


class S3Storage(FileStorageMixin):
    def __init__(self, app=None):
        self.app = app
        self.bucket_name = None
        self.endpoint_url = None
        self.acccess_key_id = None
        self.access_secret_key = None

        if app is not None:
            self.init_app(app)

    def init_app(self, app):
        self.app = app
        self.bucket_name = app.config['S3_BUCKET_NAME']
        self.endpoint_url = app.config['S3_ENDPOINT_URL']
        self.acccess_key_id = app.config['S3_ACCESS_KEY_ID']
        self.access_secret_key = app.config['S3_ACCESS_SECRET_KEY']

        self.session = boto3.session.Session()
        self.client = self.session.client(
            service_name='s3',
            endpoint_url=self.endpoint_url,
            aws_access_key_id=self.acccess_key_id,
            aws_secret_access_key=self.access_secret_key,
            region_name=app.config.get("S3_REGION_NAME"),
            config=Config(signature_version="s3v4"),
        )

    def save(self, file: File, key: str):
        self.client.put_object(
            Bucket=self.bucket_name, 
            Key=key, 
            Body=file.bytes,
            ContentType=file.content_type,
        )

    def read(self, key: str) -> File:
        response = self.client.get_object(Bucket=self.bucket_name, Key=key)
        with response["Body"] as body:
            return File(key, response["ContentType"], body.read())

    def delete(self, key):
        self.client.delete_object(
            Bucket=self.bucket_name,
            Key=key
        )

    def exists(self, key):
        try:
            self.client.head_object(Bucket=self.bucket_name, Key=key)
            return True
        except ClientError as e:
            if e.response["Error"]["Code"] in {"403", "404", "AccessDenied", "NoSuchKey", "NotFound"}:
                return False
            raise

    def get_url(self, key):
        return self.client.generate_presigned_url(
            "get_object",
            Params={"Bucket": self.bucket_name, "Key": key},
            ExpiresIn=3600,
        )

    def get_upload_url(self, key, *, content_type, size, expires_in=900):
        return self.client.generate_presigned_url(
            "put_object",
            Params={
                "Bucket": self.bucket_name,
                "Key": key,
                "ContentType": content_type,
                "ContentLength": size,
                "IfNoneMatch": "*",
            },
            ExpiresIn=expires_in,
        )
