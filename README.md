# Camelot
'Tis a silly place. 

[![Monty Python's Holy Grail Camelot Scene](https://img.youtube.com/vi/SQCArh_R9dY/0.jpg)](https://www.youtube.com/watch?v=SQCArh_R9dY)

Repository for one offs and toy models to explore random topics.

## CentroidMcCentroidface

Created to quickly assess centroid/tracking quality for the Lowell 31" at Anderson Mesa.

It turned out that when the sidereal tracking was on, we were getting a big periodic error
associated with a belt in the RA drive that needed replacing.  This is the code that 
quickly chugged thru the data to figure that out.

## CloudyMcCloudface

Prototype for assessing all sky camera images and coming up with a 'cloudiness' metric.

## GOESMcGOESface

Prototype for grabbing the current GOES-16 data and manipulating it ourselves for display,
so we don't have to depend on anything else for the DCT & NightWatch.

## WebcamMcWebcamface

Prototype for grabbing the current image from a webcam or set of webcams. 
Can be used with any webam that has a simple cgi-bin type interface that returns a picture 
when you issue an authenticated HTTP GET request to the right URL.
