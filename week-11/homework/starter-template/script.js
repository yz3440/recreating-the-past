// Week 11 - Simulation
// Emergent behavior, physics, particles, agents

let particles = [];

function setup() {
  createCanvas(800, 800);
  
  // Initialize your simulation
  
}

function draw() {
  background(255, 10);
  
  // Update and draw your simulation
  
}

class Particle {
  constructor(x, y) {
    this.pos = createVector(x, y);
    this.vel = createVector(0, 0);
    this.acc = createVector(0, 0);
  }
  
  update() {
    this.vel.add(this.acc);
    this.pos.add(this.vel);
    this.acc.mult(0);
  }
  
  applyForce(force) {
    this.acc.add(force);
  }
  
  display() {
    point(this.pos.x, this.pos.y);
  }
}
