// FrostWise 3D background: a drifting particle field that thaws from frost-blue to
// spring-green as you scroll. Three.js (module via CDN), GPU-cheap (points + shader colors),
// honours prefers-reduced-motion.
import * as THREE from 'three';

const canvas = document.getElementById('bg');
const reduced = window.matchMedia('(prefers-reduced-motion: reduce)').matches;

const renderer = new THREE.WebGLRenderer({ canvas, antialias: true, alpha: true, powerPreference: 'high-performance' });
renderer.setPixelRatio(Math.min(window.devicePixelRatio, 1.5));
renderer.setSize(window.innerWidth, window.innerHeight);

const scene = new THREE.Scene();
scene.fog = new THREE.FogExp2(0x07090d, 0.055);

const camera = new THREE.PerspectiveCamera(60, window.innerWidth / window.innerHeight, 0.1, 100);
camera.position.set(0, 0, 14);

// --- particle field ---
const COUNT = reduced ? 900 : 2200;
const positions = new Float32Array(COUNT * 3);
const seeds = new Float32Array(COUNT);
const colors = new Float32Array(COUNT * 3);

const frost = new THREE.Color('#9cc6e6');   // desaturated ice
const spring = new THREE.Color('#e8b770');  // warm amber (the single warm accent)

for (let i = 0; i < COUNT; i++) {
  positions[i * 3] = (Math.random() - 0.5) * 44;
  positions[i * 3 + 1] = (Math.random() - 0.5) * 30;
  positions[i * 3 + 2] = (Math.random() - 0.5) * 30;
  seeds[i] = Math.random() * Math.PI * 2;
  const c = frost.clone().lerp(spring, Math.random() * 0.25);
  colors[i * 3] = c.r; colors[i * 3 + 1] = c.g; colors[i * 3 + 2] = c.b;
}

const geo = new THREE.BufferGeometry();
geo.setAttribute('position', new THREE.BufferAttribute(positions, 3));
geo.setAttribute('color', new THREE.BufferAttribute(colors, 3));
geo.setAttribute('aSeed', new THREE.BufferAttribute(seeds, 1));
// per-star size variety + twinkle speed
const sizes = new Float32Array(COUNT);
const twk = new Float32Array(COUNT);
for (let i = 0; i < COUNT; i++) {
  sizes[i] = 0.5 + Math.random() * Math.random() * 2.2; // mostly small, a few bright
  twk[i] = 0.6 + Math.random() * 2.2;                    // each star twinkles at its own rate
}
geo.setAttribute('aSize', new THREE.BufferAttribute(sizes, 1));
geo.setAttribute('aTwinkle', new THREE.BufferAttribute(twk, 1));

const sprite = makeDisc();

// GPU shader: each star glows up and fades on its own cycle = a living midnight galaxy.
const mat = new THREE.ShaderMaterial({
  uniforms: {
    uTime: { value: 0 },
    uTex: { value: sprite },
    uColor: { value: frost.clone() },
    uSize: { value: (window.innerHeight / 900) * 40.0 },
  },
  transparent: true,
  depthWrite: false,
  blending: THREE.AdditiveBlending,
  vertexShader: `
    attribute float aSeed; attribute float aSize; attribute float aTwinkle;
    uniform float uTime; uniform float uSize;
    varying float vTw;
    void main(){
      // independent twinkle: brightness never drops below ~0.5 so stars stay visible
      float tw = 0.5 + 0.5 * sin(uTime * aTwinkle + aSeed * 6.2831);
      vTw = 0.5 + 0.5 * tw;
      vec4 mv = modelViewMatrix * vec4(position, 1.0);
      gl_PointSize = aSize * uSize * (1.0 / -mv.z) * (0.8 + 0.6 * tw);
      gl_Position = projectionMatrix * mv;
    }
  `,
  fragmentShader: `
    uniform sampler2D uTex; uniform vec3 uColor;
    varying float vTw;
    void main(){
      vec4 t = texture2D(uTex, gl_PointCoord);
      // Soft, lightly-visible stars: gentle brightness, twinkle adds a subtle shimmer.
      float b = 0.35 + 0.4 * vTw;
      gl_FragColor = vec4(uColor * b, 1.0) * t.a * 0.7;
    }
  `,
});
const points = new THREE.Points(geo, mat);
scene.add(points);

// A soft central glow plane for depth
const glowMat = new THREE.MeshBasicMaterial({ color: 0x9cc6e6, transparent: true, opacity: 0.05 });
const glow = new THREE.Mesh(new THREE.CircleGeometry(10, 48), glowMat);
glow.position.z = -8; scene.add(glow);

let thaw = 0;              // 0 = frost, 1 = spring (driven by scroll)
let targetThaw = 0;
let mouseX = 0, mouseY = 0;
let scrolling = false, scrollEnd;
let driftFrame = 0;

window.addEventListener('scroll', () => {
  const max = document.body.scrollHeight - window.innerHeight;
  targetThaw = max > 0 ? Math.min(1, window.scrollY / max) : 0;
  scrolling = true;
  clearTimeout(scrollEnd);
  scrollEnd = setTimeout(() => { scrolling = false; }, 160);
}, { passive: true });

window.addEventListener('pointermove', (e) => {
  mouseX = (e.clientX / window.innerWidth - 0.5);
  mouseY = (e.clientY / window.innerHeight - 0.5);
});

const base = positions.slice();
const clock = new THREE.Clock();

let last = 0;
const FRAME = 1000 / 30; // 30fps ambient twinkle is plenty and frees the main thread for scroll

function tick(now) {
  requestAnimationFrame(tick);
  if (now - last < FRAME) return;
  last = now;

  const t = clock.getElapsedTime();
  thaw += (targetThaw - thaw) * 0.08;

  // Twinkle + tint are GPU uniforms (one write each) so the galaxy keeps glowing even
  // while scrolling, with no per-vertex CPU cost.
  mat.uniforms.uTime.value = t;
  mat.uniforms.uColor.value.copy(frost.clone().lerp(spring, thaw));
  glow.material.color.copy(frost.clone().lerp(spring, thaw));

  // Gentle positional drift only when idle (keeps scroll perfectly smooth).
  if (!reduced && !scrolling && (driftFrame++ & 1) === 0) {
    const p = geo.attributes.position.array;
    for (let i = 0; i < COUNT; i++) {
      const s = seeds[i];
      p[i * 3 + 1] = base[i * 3 + 1] + Math.sin(t * 0.4 + s) * 0.5;
      p[i * 3] = base[i * 3] + Math.cos(t * 0.25 + s) * 0.35;
    }
    geo.attributes.position.needsUpdate = true;
  }

  points.rotation.y = t * 0.015 + mouseX * 0.3;
  points.rotation.x = mouseY * 0.2;
  camera.position.x += (mouseX * 2 - camera.position.x) * 0.03;
  camera.position.y += (-mouseY * 1.5 - camera.position.y) * 0.03;
  camera.lookAt(0, 0, 0);

  renderer.render(scene, camera);
}
requestAnimationFrame(tick);

window.addEventListener('resize', () => {
  camera.aspect = window.innerWidth / window.innerHeight;
  camera.updateProjectionMatrix();
  renderer.setSize(window.innerWidth, window.innerHeight);
  mat.uniforms.uSize.value = (window.innerHeight / 900) * 40.0;
});

function makeDisc() {
  const c = document.createElement('canvas'); c.width = c.height = 64;
  const g = c.getContext('2d');
  const grad = g.createRadialGradient(32, 32, 0, 32, 32, 32);
  grad.addColorStop(0, 'rgba(255,255,255,1)');
  grad.addColorStop(0.4, 'rgba(255,255,255,.7)');
  grad.addColorStop(1, 'rgba(255,255,255,0)');
  g.fillStyle = grad; g.fillRect(0, 0, 64, 64);
  const tex = new THREE.CanvasTexture(c); return tex;
}
