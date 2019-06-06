## I Walk The Line

Experiment to figure out the details of a main loop also receiving updates
via an ActiveMQ broker topic, and processing those updates/commands
and removing them from the queue. Lots and lots of little details meant
that this had to be a standalone experiment before trying to make a real
working example.

### Dear God Why

This was a fairly esoteric requirement so I couldn't find many/any good
examples out there on how to actually accomplish that.  So, I figured it out
myself.  It *doesn't* use any actual queue structures or anything fancy
like that, the commands from an external requestor are parsed by the
listener and stuffed into that listener's class; it's then periodically
checked from the main looping code to see what (if anything) is in there
and processed accordingly.
