from config import settings

print(f"API Key: {settings.deepseek_api_key[:10]}...")
print(f"Base URL: {settings.deepseek_base_url}")
print(f"Model: {settings.deepseek_model}")
print(f"Database Path: {settings.database_path}")
print(f"Chroma Path: {settings.chroma_persist_dir}")