# sorties de reference de Ruby : Random.new(seed) puis Array#sample(20) trois fois
[0, 1, 42, 12345, 4294967295, 1757829900].each do |seed|
  r = Random.new(seed)
  draws = 3.times.map { (1..80).to_a.sample(20, random: r).sort }
  puts "#{seed} " + draws.map { |d| d.join(",") }.join(" ")
end
puts "VERSION #{RUBY_VERSION}"
