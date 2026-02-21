cache.set("name", "PAPA", 60)
cache.set("version", "0.1.0")

let name = cache.get("name")
print("Cached name:", name)

let missing = cache.get("nonexistent")
print("Missing:", missing)

cache.delete("version")
let keys = cache.keys("*")
print("Keys:", keys)
