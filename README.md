# Camelot
'Tis a silly place. 

[![Monty Python's Holy Grail Camelot Scene](https://img.youtube.com/vi/SQCArh_R9dY/0.jpg)](https://www.youtube.com/watch?v=SQCArh_R9dY)

Repository for one offs and toy models to explore random topics.

## BokehMcBokehface

Prototype for figuring out the details of using bokeh server to query a database periodically
and stream updates/new data to the plot without having to force a full refresh, to be integrated
into the NightWatch project to visualize DCT data.

*Further development moved to moved to [NightShift](https://github.com/LowellObservatory/NightShift)*

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

*Further development moved to moved to [NightShift](https://github.com/LowellObservatory/NightShift)*

## RadarLove

Prototype for grabbing and plotting the current NEXRAD radar for a particular radar site.
Same raison d'être as GOESMcGOESFace.

*Further development moved to moved to [NightShift](https://github.com/LowellObservatory/NightShift)*

## WebcamMcWebcamface

Prototype for grabbing the current image from a webcam or set of webcams. 
Can be used with any webam that has a simple cgi-bin type interface that returns a picture 
when you issue an authenticated HTTP GET request to the right URL.

*Further development moved to moved to [NightShift](https://github.com/LowellObservatory/NightShift)*
