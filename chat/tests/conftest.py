import os

# Set dummy environment variables before importing deepseek
os.environ.setdefault("SUPABASE_URL", "http://dummy-supabase-url")
os.environ.setdefault("SUPABASE_KEY", "dummy_supabase_key")
os.environ.setdefault("SECRET_KEY", "dummy_secret")
os.environ.setdefault("CLIENT_XUNFEI1_API_KEY", "dummy_xunfei_key_1")
os.environ.setdefault("CLIENT_XUNFEI2_API_KEY", "dummy_xunfei_key_2")
os.environ.setdefault("CLIENT_XUNFEI_BASE_URL", "http://dummy-xunfei-api")

# Define dummy Supabase classes to simulate Supabase responses without making real API calls


class DummySupabaseTable:
    def __init__(self, data=None):
        self.data = data or []

    def select(self, columns="*"):
        self.columns = columns
        return self

    def eq(self, key, value):
        self.filter_key = key
        self.filter_value = value
        return self

    def execute(self):
        # When filtering by "user_id", return simulated data
        if hasattr(self, "filter_key") and self.filter_key == "user_id":
            return DummySupabaseResponse(
                [{"id": 1, "name": "Test Chat", "messages": {"messages": []}}]
            )
        return DummySupabaseResponse([])

    def update(self, data):
        self.updated_data = data
        return self

    def insert(self, data):
        self.inserted_data = data
        return self


class DummySupabaseResponse:
    def __init__(self, data):
        self.data = data


class DummySupabaseClient:
    def table(self, name):
        return DummySupabaseTable()


# Define a dummy create_client function that always returns a DummySupabaseClient
def dummy_create_client(supabase_url, supabase_key, options=None):
    return DummySupabaseClient()


# Override the create_client function in the low-level supabase module
import supabase._sync.client as supabase_client_module

supabase_client_module.create_client = dummy_create_client

# Also override the top-level supabase.create_client, since deepseek uses:
# from supabase import create_client
import supabase

supabase.create_client = dummy_create_client

# Now import deepseek so that it uses the dummy environment variables and dummy client
from .. import deepseek
