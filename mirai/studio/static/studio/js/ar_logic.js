import * as THREE from 'three';
import { GLTFLoader } from 'three/addons/loaders/GLTFLoader.js';

// --- Configuration ---
const CONFIG = {
    fov: 75,
    near: 0.1,
    far: 1000,
    defaultScale: 0.5,
    minScale: 0.1,
    maxScale: 2.0
};

// --- State ---
let scene, camera, renderer;
let currentModel = null;
let mixer = null;
let clock = new THREE.Clock();
let isDragging = false;
let previousTouch = null;
let initialPinchDistance = null;
let initialScale = null;

// --- Initialization ---
function init() {
    // 1. Setup Scene
    const container = document.getElementById('ar-container');
    scene = new THREE.Scene();

    // 2. Setup Camera
    const aspect = window.innerWidth / window.innerHeight;
    camera = new THREE.PerspectiveCamera(CONFIG.fov, aspect, CONFIG.near, CONFIG.far);
    camera.position.z = 5;

    // 3. Setup Renderer
    renderer = new THREE.WebGLRenderer({ alpha: true, antialias: true, preserveDrawingBuffer: true });
    renderer.setSize(window.innerWidth, window.innerHeight);
    renderer.setPixelRatio(window.devicePixelRatio);
    container.appendChild(renderer.domElement);

    // 4. Lights
    const ambientLight = new THREE.AmbientLight(0xffffff, 1);
    scene.add(ambientLight);
    
    const directionalLight = new THREE.DirectionalLight(0xffffff, 2);
    directionalLight.position.set(0, 5, 5);
    scene.add(directionalLight);

    // 5. Webcam Feed
    initWebcam();

    // 6. Event Listeners
    window.addEventListener('resize', onWindowResize, false);
    setupInteraction(container);
    setupUI();

    // 7. Load Initial Model
    const firstBtn = document.querySelector('.character-btn');
    if (firstBtn) {
        loadModel(firstBtn.dataset.model);
    }

    // 8. Animation Loop
    animate();
}

function initWebcam() {
    const video = document.getElementById('video-feed');
    if (navigator.mediaDevices && navigator.mediaDevices.getUserMedia) {
        navigator.mediaDevices.getUserMedia({ video: { facingMode: 'user' } })
            .then(function(stream) {
                video.srcObject = stream;
                video.play();
            })
            .catch(function(error) {
                console.error("Unable to access camera:", error);
                alert("Please allow camera access to use AR features.");
            });
    }
}

// --- 3D Model Handling ---
function loadModel(url) {
    if (currentModel) {
        scene.remove(currentModel);
        currentModel = null;
        mixer = null;
    }

    const loader = new GLTFLoader();
    loader.load(url, function(gltf) {
        currentModel = gltf.scene;
        
        // Center the model
        const box = new THREE.Box3().setFromObject(currentModel);
        const center = box.getCenter(new THREE.Vector3());
        currentModel.position.sub(center); // Center at 0,0,0
        
        // Scale
        currentModel.scale.set(CONFIG.defaultScale, CONFIG.defaultScale, CONFIG.defaultScale);
        
        scene.add(currentModel);

        // Animations
        if (gltf.animations && gltf.animations.length) {
            mixer = new THREE.AnimationMixer(currentModel);
            // Play all animations or just the first one
            const action = mixer.clipAction(gltf.animations[0]);
            action.play();
        }

    }, undefined, function(error) {
        console.error('An error happened loading the model:', error);
    });
}

// --- Interaction ---
function setupInteraction(container) {
    // Mouse/Touch Events for Dragging and Scaling
    
    container.addEventListener('mousedown', onPointerDown);
    container.addEventListener('mousemove', onPointerMove);
    container.addEventListener('mouseup', onPointerUp);
    
    container.addEventListener('touchstart', onTouchStart, { passive: false });
    container.addEventListener('touchmove', onTouchMove, { passive: false });
    container.addEventListener('touchend', onTouchEnd);
}

function onPointerDown(e) {
    isDragging = true;
}

function onPointerMove(e) {
    if (!isDragging || !currentModel) return;
    
    // Simple drag logic (moves model in X/Y plane)
    // Sensitivity factor
    const deltaX = e.movementX * 0.01;
    const deltaY = -e.movementY * 0.01;

    currentModel.position.x += deltaX;
    currentModel.position.y += deltaY;
}

function onPointerUp() {
    isDragging = false;
}

// Touch logic for pinch-to-zoom and drag
function onTouchStart(e) {
    if (e.touches.length === 1) {
        isDragging = true;
        previousTouch = e.touches[0];
    } else if (e.touches.length === 2) {
        isDragging = false;
        initialPinchDistance = getDistance(e.touches[0], e.touches[1]);
        if (currentModel) {
            initialScale = currentModel.scale.x;
        }
    }
}

function onTouchMove(e) {
    e.preventDefault(); // Prevent scrolling

    if (e.touches.length === 1 && isDragging && currentModel) {
        const touch = e.touches[0];
        const deltaX = (touch.clientX - previousTouch.clientX) * 0.01;
        const deltaY = -(touch.clientY - previousTouch.clientY) * 0.01;
        
        currentModel.position.x += deltaX;
        currentModel.position.y += deltaY;
        
        previousTouch = touch;
    } else if (e.touches.length === 2 && currentModel) {
        const currentDistance = getDistance(e.touches[0], e.touches[1]);
        if (initialPinchDistance > 0) {
            const scaleFactor = currentDistance / initialPinchDistance;
            const newScale = Math.min(Math.max(initialScale * scaleFactor, CONFIG.minScale), CONFIG.maxScale);
            currentModel.scale.set(newScale, newScale, newScale);
        }
    }
}

function onTouchEnd() {
    isDragging = false;
    initialPinchDistance = null;
}

function getDistance(touch1, touch2) {
    const dx = touch1.clientX - touch2.clientX;
    const dy = touch1.clientY - touch2.clientY;
    return Math.sqrt(dx * dx + dy * dy);
}

// --- UI Logic ---
function setupUI() {
    // Character Selection
    const buttons = document.querySelectorAll('.character-btn');
    buttons.forEach(btn => {
        btn.addEventListener('click', (e) => {
            // Update active state
            buttons.forEach(b => b.classList.remove('ring-2', 'ring-yellow-400'));
            const target = e.currentTarget;
            target.classList.add('ring-2', 'ring-yellow-400');
            
            // Load model
            loadModel(target.dataset.model);
        });
    });

    // Capture Button
    const captureBtn = document.getElementById('capture-btn');
    captureBtn.addEventListener('click', takePhoto);
}

function takePhoto() {
    // Flash effect
    const flash = document.getElementById('flash');
    flash.classList.remove('opacity-0');
    setTimeout(() => flash.classList.add('opacity-0'), 100);

    // 1. Create a canvas to combine video and 3D
    const video = document.getElementById('video-feed');
    const canvas = document.createElement('canvas');
    canvas.width = video.videoWidth;
    canvas.height = video.videoHeight;
    const ctx = canvas.getContext('2d');

    // 2. Draw Video (Mirrored)
    ctx.save();
    ctx.scale(-1, 1);
    ctx.drawImage(video, -canvas.width, 0, canvas.width, canvas.height);
    ctx.restore();

    // 3. Draw 3D Scene
    // We need to render the 3D scene to its canvas first
    renderer.render(scene, camera);
    // Then draw that canvas onto our capture canvas
    // Note: This might need adjustment for aspect ratio matching
    ctx.drawImage(renderer.domElement, 0, 0, canvas.width, canvas.height);

    // 4. Download
    const dataURL = canvas.toDataURL('image/png');
    const link = document.createElement('a');
    link.download = `self-studio-ar-${Date.now()}.png`;
    link.href = dataURL;
    link.click();
}

// --- Loop ---
function onWindowResize() {
    camera.aspect = window.innerWidth / window.innerHeight;
    camera.updateProjectionMatrix();
    renderer.setSize(window.innerWidth, window.innerHeight);
}

function animate() {
    requestAnimationFrame(animate);
    
    const delta = clock.getDelta();
    if (mixer) mixer.update(delta);

    renderer.render(scene, camera);
}

// Start
init();
