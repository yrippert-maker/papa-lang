let x = 42
match x {
  0 => { print "zero" }
  1..10 => { print "small" }
  10..100 => { print "medium" }
  _ => { print "large" }
}
print "done"
