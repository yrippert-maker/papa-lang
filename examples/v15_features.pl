// PAPA Lang v1.5 features demo

// 1. Pattern matching
let x = 42
match x {
  0 => { print("zero") }
  1..10 => { print("small") }
  10..100 => { print("medium") }
  _ => { print("large") }
}

// 2. Pipeline
fn double(n) { n * 2 }
let y = 5 |> double()
print(y)

// 3. List comprehension
let squares = [n * n for n in [1, 2, 3, 4, 5] if n > 2]
print(squares)

// 4. Result + ?
let r = ok(100)
let v = r?
print(v)

// 5. Struct literal
let u = User { name: "alice", email: "a@b.com" }
print(u)
