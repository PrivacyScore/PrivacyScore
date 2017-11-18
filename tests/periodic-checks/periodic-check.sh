#!/bin/bash

tmpfile=`mktemp`
testssl="../vendor/testssl.sh/testssl.sh -Z --warnings=batch --quiet --jsonfile-pretty $tmpfile --append"


host1="ssl.exoneon.de"
host2="privacyscoretest.pwsrv.de"

# 1st parameter: maximum number of seconds to sleep
if [ "$1" != "" ]
then
    sleep $[ ( $RANDOM % $1 )  + 1 ]s
fi

$testssl $host1 >/dev/null 2>/dev/null

#cp $tmpfile periodic-check-template-$host1-https.json 

problem1=0

# the commented alternative must be used if --quiet is not used with testssl.sh
#difference1=`diff <(tail -n +9 $tmpfile | head -n -2) <(tail -n +9 periodic-check-template-$host1-https.json | head -n -2)`
difference1=`diff $tmpfile periodic-check-template-$host1-https.json`

if [ $? -ne 0 ]; then
    problem1=1
    echo "PROBLEM1=1"
fi

truncate -s 0 "$tmpfile"


$testssl $host2 >/dev/null 2>/dev/null

#cp $tmpfile periodic-check-template-$host2-https.json 

problem2=0

#difference2=`diff <(tail -n +9 $tmpfile | head -n -2) <(tail -n +9 periodic-check-template-$host2-https.json | head -n -2)`
difference2=`diff $tmpfile periodic-check-template-$host2-https.json`

if [ $? -ne 0 ]; then
    problem2=1
    echo "PROBLEM2=1"
fi


if [ $problem1 -ne 0 ] && [ $problem2 -ne 0 ]
then
    echo "Test results for HTTPS differ from expectation for both hosts!"
    echo "Host 1: $host1"
    echo $difference1
    echo ""
    echo "Host 2: $host2"
    echo $difference2
fi

truncate -s 0 "$tmpfile"



testssl="$testssl -t smtp"


$testssl $host1:25 >/dev/null 2>/dev/null

#cp $tmpfile periodic-check-template-$host1-starttls.json 

problem1=0

#difference1=`diff <(tail -n +9 $tmpfile | head -n -2) <(tail -n +9 periodic-check-template-$host1-starttls.json | head -n -2)`
difference1=`diff $tmpfile periodic-check-template-$host1-starttls.json`

if [ $? -ne 0 ]; then
    problem1=1
fi


truncate -s 0 "$tmpfile"

$testssl $host2:25 >/dev/null 2>/dev/null

#cp $tmpfile periodic-check-template-$host2-starttls.json 

problem2=0

#difference2=`diff <(tail -n +9 $tmpfile | head -n -2) <(tail -n +9 periodic-check-template-$host2-starttls.json | head -n -2)`
difference2=`diff $tmpfile periodic-check-template-$host2-starttls.json`

if [ $? -ne 0 ]; then
    problem2=1
fi


if [ $problem1 -ne 0 ] && [ $problem2 -ne 0 ]
then
    echo "Test results for SMTP/STARTTLS differ from expectation for both hosts!"
    echo "Host 1: $host1"
    echo $difference1
    echo ""
    echo "Host 2: $host2"
    echo $difference2
fi

rm "$tmpfile"
