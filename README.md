# CartoDB table to GeoRSS feed

This is an AppEngine app to very simply, turn any table on CartoDB into a GeoRSS feed. 

## Motivation

I wanted to link a table on CartoDB to an [IFTTT](www.ifttt.com) recipe. Since IFTTT doesn't support CartoDB APIs out of the box, I needed to somehow use one of their existing sources. An RSS feed seemed like a good fit, and with GeoRSS it made, at least some, sense to use that option. 

## Design

The app works with any username/tablename pair on CartoDB.com. You can access a table feed through,

    appname.appspot.com/{{username}}/{{tablename}}/feed.xml

That call will check the table to see if any changes have been made since last called. If so, it gets the *latests 100* changes and releases the feed. If no change has been made, it will report the cached feed. 

#### Totally not proper RSS

I know, it was more a test. If you want to send any Pull requests, I'd be happy to work with you to make this better.

:)