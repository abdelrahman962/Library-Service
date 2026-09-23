from redis_cache import (
    get_cache,
    set_cache,
    delete_cache
)
key = "library:test"
print("Before:", get_cache(key))

set_cache(
    key,
    {
        "message":"Hello Redis",
        "number":123
    },

)

print("After: ",get_cache(key))

delete_cache(key)
print("After delete: ",get_cache(key))
