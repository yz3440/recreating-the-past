// Week 8 - Woody/Steina Vasulka / Rosa Menkman Recreation
// Glitch

let img;

function preload() {
  // Load an image to glitch
  // img = loadImage('your-image.jpg');
}

function setup() {
  createCanvas(800, 800);
}

function draw() {
  background(0);
  
  // Your glitch recreation code here
  
}

// Helper function to corrupt image data
function glitchImage(img) {
  img.loadPixels();
  
  // Manipulate pixels here
  
  img.updatePixels();
  return img;
}
