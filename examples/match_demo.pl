// PAPA Lang v1.5 - Match demo
let x = 42
match x {
  0 => { print "zero" }
  1..10 => { print "small" }
  10..100 => { print "medium" }
  _ => { print "large" }
}

let res = ok("hello")
match res {
  Ok(s) => { print s }
  Err(e) => { print "error: " e }
}

let m = { "a": 1, "b": 2 }
match m {
  { "a": v } => { print "a is" v }
  _ => { print "no a" }
}

let n = 5
match n {
  k if k > 3 => { print "gt 3:" k }
  _ => { print "leq 3" }
}
