#!/usr/bin/env ruby

require 'ipaddr'
require 'resolv'
require 'json'

result = {}

# http://stackoverflow.com/questions/8539258/after-symlinking-a-file-how-do-i-get-the-path-of-the-original-file-in-ruby
curdir = __dir__

LOOKUP_CMD_1="mmdblookup -f #{curdir}/vendor/geoip/GeoLite2-Country.mmdb --ip #IP# country names en | grep -o '\".*\"' | tr -d '\"'"
LOOKUP_CMD_2="mmdblookup -f #{curdir}/vendor/geoip/GeoLite2-Country.mmdb --ip #IP# continent names en | grep -o '\".*\"' | tr -d '\"'"

def getloc(ip_array)
  locations = []
  ip_array.each do |ip|
    cmd=LOOKUP_CMD_1.sub("#IP#", ip)
    #STDERR.puts("=> #{cmd}")
		location=`#{cmd}`.chomp rescue ""
    if location==""
			cmd=LOOKUP_CMD_2.sub("#IP#", ip)
			#STDERR.puts("=> #{cmd}")
			location=`#{cmd}`.chomp rescue ""
    end
    locations << location
  end
  locations
end

def getcname(host)
  res = nil
	Resolv::DNS.open do |dns|
		res = dns.getresource(host, Resolv::DNS::Resource::IN::CNAME).name rescue nil
  end
	res
end

def getmxname(host)
	if host[/^www\./]
		host = host[4..-1]
	end
  mx_addresses = []
  Resolv::DNS.open do |dns|
		ress = dns.getresources(host, Resolv::DNS::Resource::IN::MX) rescue []
    mx_addresses = []
    ress.map { |r| mx_addresses << r.exchange.to_s }
  end
  mx_addresses
end


### MAIN PROGRAM ###

begin
  host = ARGV[0]
rescue
  STDERR.puts("=> Error: Provide hostname as first argument")
  exit(1)
end

if host[/^(https|http)?(:\/\/)?([^\/]*)\/?/]
	host = $3
end

#STDERR.puts "=> Host: #{host}"

cname = getcname(host)
result["A_CNAME"] = cname

ip_addresses = Resolv.getaddresses(host)
result["A_ADDRESSES"] = ip_addresses.join(", ")

reverse_names = ip_addresses.map{|ip| Resolv.getnames(ip) rescue []}.flatten
result["A_REVERSE_LOOKUP"] = reverse_names.join(", ")

a_locations = getloc(ip_addresses)
result["A_LOCATIONS"] = a_locations.uniq.sort.join(", ")

mx_names = getmxname(host)
result["MX_NAMES"] = mx_names.join(", ")

mx_cnames = mx_names.map{|name| getcname(name)}.uniq
result["MX_CNAMES"] = mx_cnames.join(", ")

mx_ip_addresses = mx_names.map{|name| Resolv.getaddresses(name) rescue []}.flatten
result["MX_ADDRESSES"] = mx_ip_addresses.join(", ")

mx_reverse_names = mx_ip_addresses.map{|ip| Resolv.getnames(ip) rescue []}.flatten
result["MX_REVERSE_LOOKUP"] = mx_reverse_names.join(", ")

mx_locations = getloc(mx_ip_addresses)
result["MX_LOCATIONS"] = mx_locations.uniq.sort.join(", ")

#result.each_pair do |key,val|
#  puts "#{key}:#{val}"
#end

puts result.to_json
