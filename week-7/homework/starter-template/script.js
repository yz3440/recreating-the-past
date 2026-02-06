// Week 7 - Myron Krueger / Camille Utterback Recreation
// Body / Interactive

let video;
let bodyPose;
let poses = [];

function preload() {
  // Load body tracking model if needed
  // bodyPose = ml5.bodyPose();
}

function setup() {
  createCanvas(640, 480);
  
  // Setup video capture
  // video = createCapture(VIDEO);
  // video.size(640, 480);
  // video.hide();
  
  // Start detecting poses
  // bodyPose.detectStart(video, gotPoses);
}

function draw() {
  background(0);
  
  // Your recreation code here
  
}

function gotPoses(results) {
  poses = results;
}
