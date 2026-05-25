from export_dotenv.use_case import fetch_environment_values
from export_dotenv_test_utils.fake import create_fake_kube_facade
from kubek.kube.dto.kind import Kind

api = create_fake_kube_facade()


def test_workflowtemplate_env_vars():
    kind = Kind.WORKFLOWTEMPLATE
    name = "data-processor"
    tested = fetch_environment_values(
        kind=kind,
        name=name,
        api=api,
    )

    assert tested == {
        "APP_ENV": "local",
        "DATABASE_HOST": "postgres.demo.svc.cluster.local",
        "DATABASE_PORT": "5432",
        "FEATURE_FLAG_NEW_UI": "true",
        "LOG_LEVEL": "debug",
        "MAX_CONNECTIONS": "20",
        "SERVICE_TIMEOUT_MS": "3000",
        "API_KEY": "myapikey123",
        "DATABASE_PASSWORD": "secretpassword",
        "JWT_SECRET": "jwt-secret-token-xyz",
        "REDIS_URL": "redis://redis.demo.svc.cluster.local:6379",
        "S3_ACCESS_KEY": "s3-access-key-abc",
        "BATCH_SIZE": "{{inputs.parameters.batch_size}}",
        "SOURCE_BUCKET": "{{inputs.parameters.source_bucket}}",
        "DB_HOST": "postgres.demo.svc.cluster.local",
    }


def test_deployment_env_vars():
    kind = Kind.DEPLOYMENT
    name = "api-service"
    tested = fetch_environment_values(
        kind=kind,
        name=name,
        api=api,
    )

    assert tested == {
        "APP_ENV": "local",
        "DATABASE_HOST": "postgres.demo.svc.cluster.local",
        "DATABASE_PORT": "5432",
        "FEATURE_FLAG_NEW_UI": "true",
        "LOG_LEVEL": "debug",
        "MAX_CONNECTIONS": "20",
        "SERVICE_TIMEOUT_MS": "3000",
        "API_KEY": "myapikey123",
        "DATABASE_PASSWORD": "secretpassword",
        "JWT_SECRET": "jwt-secret-token-xyz",
        "REDIS_URL": "redis://redis.demo.svc.cluster.local:6379",
        "S3_ACCESS_KEY": "s3-access-key-abc",
        "DB_PASSWORD": "secretpassword",
        "LOG_LEVEL_OVERRIDE": "debug",
        "DIRECT_VALUE": "hello-from-api",
        "API_VERSION": "v2",
        "ENABLE_TRACING": "true",
    }
