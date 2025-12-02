import * as THREE from 'three';
import { GLTFLoader } from 'three/addons/loaders/GLTFLoader.js';
import { OBJLoader } from 'three/addons/loaders/OBJLoader.js';
import { MTLLoader } from 'three/addons/loaders/MTLLoader.js';

/**
 * ARManager
 * Handles the 3D scene, model loading, and user interactions for the AR experience.
 */
class ARManager {
    constructor(containerId) {
        this.container = document.getElementById(containerId);
        if (!this.container) {
            console.error(`AR Container #${containerId} not found!`);
            return;
        }

        // Configuration
        this.config = {
            fov: 75,
            near: 0.1,
            far: 1000,
            defaultScale: 0.5,
            minScale: 0.1,
            maxScale: 2.0
        };

        // State
        this.scene = null;
        this.camera = null;
        this.renderer = null;
        this.currentModel = null;
        this.mixer = null;
        this.clock = new THREE.Clock();
        
        // Interaction State
        this.isDragging = false;
        this.previousTouch = null;
        this.initialPinchDistance = null;
        this.initialScale = null;

        // Initialize
        this.init();
    }

    init() {
        console.log("Initializing ARManager...");
        this.setupScene();
        this.setupLights();
        this.setupRenderer();
        this.setupInteraction();
        this.setupUI();
        
        // Start Loop
        this.animate = this.animate.bind(this);
        this.animate();

        // Handle Resize
        window.addEventListener('resize', () => this.onWindowResize(), false);

        // Load Initial Model if present in UI
        const firstBtn = document.querySelector('.character-btn');
        if (firstBtn && firstBtn.dataset.model) {
            this.loadModel(firstBtn.dataset.model);
            // Set active state
            firstBtn.classList.add('active', 'ring-2', 'ring-white');
        }
    }

    setupScene() {
        this.scene = new THREE.Scene();
        const aspect = window.innerWidth / window.innerHeight;
        this.camera = new THREE.PerspectiveCamera(this.config.fov, aspect, this.config.near, this.config.far);
        this.camera.position.z = 5;
    }

    setupLights() {
        const ambientLight = new THREE.AmbientLight(0xffffff, 1.5);
        this.scene.add(ambientLight);

        const directionalLight = new THREE.DirectionalLight(0xffffff, 2);
        directionalLight.position.set(0, 5, 5);
        this.scene.add(directionalLight);
    }

    setupRenderer() {
        this.renderer = new THREE.WebGLRenderer({ 
            alpha: true, 
            antialias: true, 
            preserveDrawingBuffer: true 
        });
        this.renderer.setSize(window.innerWidth, window.innerHeight);
        this.renderer.setPixelRatio(window.devicePixelRatio);
        this.container.appendChild(this.renderer.domElement);
    }

    // --- Model Loading ---

    loadModel(url) {
        console.log("Loading model:", url);
        this.clearModel();

        url = decodeURIComponent(url);
        const isObj = url.toLowerCase().endsWith('.obj');

        if (isObj) {
            this._loadOBJ(url);
        } else {
            this._loadGLTF(url);
        }
    }

    _loadOBJ(url) {
        const mtlUrl = url.replace('.obj', '.mtl');
        const path = url.substring(0, url.lastIndexOf('/') + 1);
        
        const mtlLoader = new MTLLoader();
        mtlLoader.setPath(path);

        mtlLoader.load(
            mtlUrl.substring(mtlUrl.lastIndexOf('/') + 1),
            (materials) => {
                materials.preload();
                const objLoader = new OBJLoader();
                objLoader.setMaterials(materials);
                objLoader.load(url, (obj) => this.onModelLoaded(obj, false), 
                    undefined, 
                    (err) => console.error("Error loading OBJ:", err)
                );
            },
            undefined,
            (err) => {
                console.warn("MTL failed, loading OBJ only.", err);
                // Fallback
                const objLoader = new OBJLoader();
                objLoader.load(url, (obj) => {
                    // Apply magenta debug material
                    obj.traverse(child => {
                        if (child.isMesh) child.material = new THREE.MeshStandardMaterial({ color: 0xff00ff });
                    });
                    this.onModelLoaded(obj, false);
                });
            }
        );
    }

    _loadGLTF(url) {
        const loader = new GLTFLoader();
        loader.load(url, (gltf) => this.onModelLoaded(gltf, true), undefined, (err) => console.error("GLTF Error:", err));
    }

    onModelLoaded(loadedData, isGltf) {
        this.currentModel = isGltf ? loadedData.scene : loadedData;

        // Center
        const box = new THREE.Box3().setFromObject(this.currentModel);
        const center = box.getCenter(new THREE.Vector3());
        this.currentModel.position.sub(center);

        // Scale
        this.currentModel.scale.set(this.config.defaultScale, this.config.defaultScale, this.config.defaultScale);

        // Force Opacity (Fix Ghosting)
        this.currentModel.traverse((child) => {
            if (child.isMesh) {
                child.castShadow = true;
                child.receiveShadow = true;
                if (child.material) {
                    const materials = Array.isArray(child.material) ? child.material : [child.material];
                    materials.forEach(mat => {
                        mat.transparent = false;
                        mat.opacity = 1.0;
                        mat.side = THREE.DoubleSide;
                        mat.depthWrite = true;
                    });
                }
            }
        });

        this.scene.add(this.currentModel);

        // Animation
        if (isGltf && loadedData.animations && loadedData.animations.length) {
            this.mixer = new THREE.AnimationMixer(this.currentModel);
            this.mixer.clipAction(loadedData.animations[0]).play();
        }
        
        // Update Slider if exists
        const slider = document.getElementById('scale-slider');
        if (slider) slider.value = this.config.defaultScale;
    }

    clearModel() {
        if (this.currentModel) {
            this.scene.remove(this.currentModel);
            this.currentModel = null;
            this.mixer = null;
        }
    }

    // --- Interaction ---

    setupInteraction() {
        // Mouse
        this.container.addEventListener('mousedown', (e) => this.onPointerDown(e));
        this.container.addEventListener('mousemove', (e) => this.onPointerMove(e));
        this.container.addEventListener('mouseup', () => this.onPointerUp());
        this.container.addEventListener('wheel', (e) => this.onWheel(e), { passive: false });

        // Touch
        this.container.addEventListener('touchstart', (e) => this.onTouchStart(e), { passive: false });
        this.container.addEventListener('touchmove', (e) => this.onTouchMove(e), { passive: false });
        this.container.addEventListener('touchend', () => this.onTouchEnd());
    }

    // Raycasting Helper
    _raycast(x, y) {
        if (!this.currentModel) return [];
        const raycaster = new THREE.Raycaster();
        const mouse = new THREE.Vector2();
        mouse.x = (x / window.innerWidth) * 2 - 1;
        mouse.y = -(y / window.innerHeight) * 2 + 1;
        raycaster.setFromCamera(mouse, this.camera);
        return raycaster.intersectObjects([this.currentModel], true);
    }

    onPointerDown(e) {
        const intersects = this._raycast(e.clientX, e.clientY);
        if (intersects.length > 0) {
            this.isDragging = true;
            this._showHelper(true);
        } else {
            this.isDragging = false;
            this._showHelper(false);
        }
    }

    onPointerMove(e) {
        // Cursor
        const intersects = this._raycast(e.clientX, e.clientY);
        document.body.style.cursor = intersects.length > 0 ? 'pointer' : 'default';

        if (!this.isDragging || !this.currentModel) return;

        // Drag Logic (Camera Plane)
        const factor = 0.005 * (this.camera.position.z / 2);
        this.currentModel.position.x += e.movementX * factor;
        this.currentModel.position.y -= e.movementY * factor;
        
        this._updateHelper();
    }

    onPointerUp() {
        this.isDragging = false;
    }

    onWheel(e) {
        e.preventDefault();
        if (!this.currentModel) return;
        
        const delta = -Math.sign(e.deltaY) * 0.1;
        this._applyScale(delta);
    }

    // Touch Logic
    onTouchStart(e) {
        if (e.touches.length === 1) {
            const touch = e.touches[0];
            const intersects = this._raycast(touch.clientX, touch.clientY);
            if (intersects.length > 0) {
                this.isDragging = true;
                this.previousTouch = touch;
                this._showHelper(true);
            } else {
                this.isDragging = false;
                this._showHelper(false);
            }
        } else if (e.touches.length === 2) {
            this.isDragging = false;
            this.initialPinchDistance = this._getDistance(e.touches[0], e.touches[1]);
            if (this.currentModel) this.initialScale = this.currentModel.scale.x;
        }
    }

    onTouchMove(e) {
        e.preventDefault();
        if (e.touches.length === 1 && this.isDragging && this.currentModel) {
            const touch = e.touches[0];
            const factor = 0.005 * (this.camera.position.z / 2);
            const dx = (touch.clientX - this.previousTouch.clientX) * factor;
            const dy = -(touch.clientY - this.previousTouch.clientY) * factor; // Invert Y
            
            this.currentModel.position.x += dx;
            this.currentModel.position.y += dy;
            this.previousTouch = touch;
            this._updateHelper();

        } else if (e.touches.length === 2 && this.currentModel && this.initialPinchDistance) {
            const dist = this._getDistance(e.touches[0], e.touches[1]);
            const scaleFactor = dist / this.initialPinchDistance;
            const newScale = this.initialScale * scaleFactor;
            this.setScale(newScale);
        }
    }

    onTouchEnd() {
        this.isDragging = false;
        this.initialPinchDistance = null;
    }

    _getDistance(t1, t2) {
        const dx = t1.clientX - t2.clientX;
        const dy = t1.clientY - t2.clientY;
        return Math.sqrt(dx*dx + dy*dy);
    }

    _showHelper(visible) {
        if (!this.currentModel) return;
        if (!this.currentModel.userData.helper) {
            const helper = new THREE.BoxHelper(this.currentModel, 0xffff00);
            this.scene.add(helper);
            this.currentModel.userData.helper = helper;
        }
        this.currentModel.userData.helper.visible = visible;
    }

    _updateHelper() {
        if (this.currentModel && this.currentModel.userData.helper) {
            this.currentModel.userData.helper.update();
        }
    }

    // --- Scaling ---

    _applyScale(delta) {
        if (!this.currentModel) return;
        const newScale = this.currentModel.scale.x + delta;
        this.setScale(newScale);
    }

    setScale(val) {
        if (!this.currentModel) return;
        const clamped = Math.min(Math.max(val, this.config.minScale), this.config.maxScale);
        this.currentModel.scale.set(clamped, clamped, clamped);
        
        // Sync UI
        const slider = document.getElementById('scale-slider');
        if (slider) slider.value = clamped;
    }

    // --- UI & Loop ---

    setupUI() {
        // Character Buttons
        document.querySelectorAll('.character-btn').forEach(btn => {
            btn.addEventListener('click', (e) => {
                const target = e.currentTarget;
                
                // Update Active UI
                document.querySelectorAll('.character-btn').forEach(b => b.classList.remove('active', 'ring-2', 'ring-white'));
                target.classList.add('active', 'ring-2', 'ring-white');

                if (target.dataset.model) {
                    this.loadModel(target.dataset.model);
                } else {
                    this.clearModel();
                }
            });
        });

        // Scale Slider
        const slider = document.getElementById('scale-slider');
        if (slider) {
            slider.addEventListener('input', (e) => {
                this.setScale(parseFloat(e.target.value));
            });
        }
    }

    onWindowResize() {
        if (!this.camera || !this.renderer) return;
        this.camera.aspect = window.innerWidth / window.innerHeight;
        this.camera.updateProjectionMatrix();
        this.renderer.setSize(window.innerWidth, window.innerHeight);
    }

    animate() {
        requestAnimationFrame(this.animate);
        const delta = this.clock.getDelta();
        if (this.mixer) this.mixer.update(delta);
        if (this.renderer && this.scene && this.camera) {
            this.renderer.render(this.scene, this.camera);
        }
    }

    takePhoto() {
        console.log("Taking photo...");
        const flash = document.getElementById('flash');
        if (flash) {
            flash.classList.remove('opacity-0');
            setTimeout(() => flash.classList.add('opacity-0'), 100);
        }

        const video = document.getElementById('video-feed');
        const canvas = document.createElement('canvas');
        canvas.width = video.naturalWidth || 1280;
        canvas.height = video.naturalHeight || 720;
        const ctx = canvas.getContext('2d');

        // Draw Video (Mirrored)
        ctx.save();
        ctx.scale(-1, 1);
        ctx.drawImage(video, -canvas.width, 0, canvas.width, canvas.height);
        ctx.restore();

        // Draw AR
        if (this.renderer && this.scene && this.camera) {
            // Hide helper
            let helperVisible = false;
            if (this.currentModel && this.currentModel.userData.helper) {
                helperVisible = this.currentModel.userData.helper.visible;
                this.currentModel.userData.helper.visible = false;
            }

            this.renderer.render(this.scene, this.camera);
            ctx.drawImage(this.renderer.domElement, 0, 0, canvas.width, canvas.height);

            // Restore helper
            if (this.currentModel && this.currentModel.userData.helper) {
                this.currentModel.userData.helper.visible = helperVisible;
            }
        }

        // Download
        const link = document.createElement('a');
        link.download = `self-studio-ar-${Date.now()}.png`;
        link.href = canvas.toDataURL('image/png');
        link.click();
    }
}

// Initialize and Expose
const arManager = new ARManager('ar-container');
window.arManager = arManager;
window.takePhoto = () => arManager.takePhoto();
window.clearModel = () => arManager.clearModel();
