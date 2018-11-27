## Webcam Mc Webcamface

Experiment to grab the latest images from either a single or a set
of IP webcams.  Specifically this is known to work with:

- TRENDnet TV-IP662PI
- D-Link DCS-3420

Or any camera with a simple cgi-bin type interface that returns a picture
when you issue an authenticated HTTP GET request to a specific endpoint.

Usually this can be figured out pretty quickly by logging in to the camera
and using your browser's development tools/console to look at either the
image source or the javascript embedded in that page.

I'm not going to tell you how to figure it out for your arbitary camera so
don't ask.

This could be extended pretty easily to pick up an RTSP stream from a given
camera, which would likely give you a higher resolution result.  I'll call
that "future work" with no timeline.


### Dear God Why

Because an observatory almost always needs to do this to monitor assets of all
types (telescopes, instruments, helium compressors, etc.) but the existing
solutions were either too heavy handed or too specific.
