// Test built-in database
db.sql("CREATE TABLE users (id TEXT, name TEXT, email TEXT)")

db.insert("users", { id: "1", name: "Alex", email: "alex@papa.dev" })
db.insert("users", { id: "2", name: "Sam", email: "sam@papa.dev" })

let users = db.query("users")
print("All users:", users)

let alex = db.find("users", "1")
print("Found:", alex)

db.delete("users", "2")
let remaining = db.query("users")
print("After delete:", remaining)
