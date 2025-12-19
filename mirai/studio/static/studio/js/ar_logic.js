import * as THREE from 'three';
import { GLTFLoader } from 'three/addons/loaders/GLTFLoader.js';
import { OBJLoader } from 'three/addons/loaders/OBJLoader.js';
import { MTLLoader } from 'three/addons/loaders/MTLLoader.js';
import { FBXLoader } from 'three/addons/loaders/FBXLoader.js';

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
            maxScale: 5.0,
            maxModels: 2
        };

        // State
        this.scene = null;
        this.camera = null;
        this.renderer = null;
        this.models = []; // Array to hold multiple models
        this.selectedModel = null; // The model currently being interacted with
        this.mixers = []; // Array of mixers
        this.clock = new THREE.Clock();
        
        // Interaction State
        this.isDragging = false;
        this.previousTouch = null;
        this.previousMousePosition = { x: 0, y: 0 };
        this.initialPinchDistance = null;
        this.initialScale = null;
        
        // Mode
        this.isAddMode = false;

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

        // Load Initial Model if present in UI (only if not empty)
        // We'll let the user click to load to avoid confusion with multiple slots
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

    toggleAddMode(enabled) {
        this.isAddMode = enabled;
        console.log("Add Mode:", this.isAddMode);
    }

    loadModel(url) {
        console.log("Loading model:", url);

        if (!this.isAddMode) {
            // Replace Mode: Clear all and load new
            this.clearAllModels();
        } else {
            // Add Mode: Check limit
            if (this.models.length >= this.config.maxModels) {
                console.warn("Max models reached. Replacing selected or last added.");
                if (this.selectedModel) {
                    this.removeModel(this.selectedModel);
                } else {
                    // Remove the oldest one (first in array)
                    this.removeModel(this.models[0]);
                }
            }
        }

        const isObj = url.toLowerCase().endsWith('.obj');
        const isFbx = url.toLowerCase().endsWith('.fbx');
        const isImg = /\.(png|jpg|jpeg)$/i.test(url);

        if (isObj) {
            this._loadOBJ(url);
        } else if (isFbx) {
            this._loadFBX(url);
        } else if (isImg) {
            this._loadImage(url);
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

    _loadFBX(url) {
        const loader = new FBXLoader();
        loader.load(url, (fbx) => this.onModelLoaded(fbx, false, true), undefined, (err) => console.error("FBX Error:", err));
    }

    _loadImage(url) {
        const loader = new THREE.TextureLoader();
        loader.load(url, (texture) => {
            const material = new THREE.SpriteMaterial({ map: texture });
            const sprite = new THREE.Sprite(material);
            sprite.scale.set(1, texture.image.height / texture.image.width, 1);
            // Pass true for isSprite
            this.onModelLoaded(sprite, false, false, true);
        }, undefined, (err) => console.error("Image Error:", err));
    }

    onModelLoaded(loadedData, isGltf, isFbx = false, isSprite = false) {
        let model = isGltf ? loadedData.scene : loadedData;

        // Center
        const box = new THREE.Box3().setFromObject(model);
        const center = box.getCenter(new THREE.Vector3());
        model.position.sub(center);

        // Auto-Scale Logic
        // Normalize to fit within a target size (e.g., 3 units height)
        const size = box.getSize(new THREE.Vector3());
        const maxDim = Math.max(size.x, size.y, size.z);
        // Larger target for sprites (they feel smaller)
        const targetSize = isSprite ? 2.5 : 1.5; 
        
        let scaleFactor = targetSize / maxDim;
        
        // Prevent upsizing too much if model is tiny, but definitely downsize if huge
        // Also respect config limits if possible, but auto-scale should override default
        if (!isFinite(scaleFactor) || scaleFactor === 0) scaleFactor = 1.0;
        
        this.config.defaultScale = scaleFactor; // Update default for this model
        model.scale.set(scaleFactor, scaleFactor, scaleFactor);

        // Rotation (Face Camera)
        model.rotation.y = Math.PI; // Face front
        model.rotation.x = 0;
        model.rotation.z = 0;

        // Offset if multiple models to avoid overlap
        if (this.models.length > 0) {
            model.position.x += 1.0; // Simple offset
        }

        // Force Opacity (Fix Ghosting)
        model.traverse((child) => {
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

        this.scene.add(model);
        this.models.push(model);
        this.selectModel(model);

        // Animation
        if (isGltf && loadedData.animations && loadedData.animations.length) {
            const mixer = new THREE.AnimationMixer(model);
            mixer.clipAction(loadedData.animations[0]).play();
            this.mixers.push(mixer);
            model.userData.mixer = mixer; // Link mixer to model
        } else if (isFbx && model.animations && model.animations.length) {
            const mixer = new THREE.AnimationMixer(model);
            const action = mixer.clipAction(model.animations[0]);
            action.play();
            this.mixers.push(mixer);
            model.userData.mixer = mixer;
        }
        
        // Update Slider if exists
        const slider = document.getElementById('scale-slider');
        if (slider) slider.value = this.config.defaultScale;
    }

    removeModel(model) {
        if (!model) return;
        
        this.scene.remove(model);
        
        // Remove from array
        const index = this.models.indexOf(model);
        if (index > -1) {
            this.models.splice(index, 1);
        }

        // Remove mixer
        if (model.userData.mixer) {
            const mIndex = this.mixers.indexOf(model.userData.mixer);
            if (mIndex > -1) this.mixers.splice(mIndex, 1);
        }

        if (model.userData.helper) {
            this.scene.remove(model.userData.helper);
            model.userData.helper.geometry.dispose();
            model.userData.helper = null;
        }

        if (this.selectedModel === model) {
            this.selectedModel = null;
        }
    }

    clearAllModels() {
        // Create a copy to iterate safely
        const models = [...this.models];
        models.forEach(m => this.removeModel(m));
    }

    selectModel(model) {
        this.selectedModel = model;
        // Hide helpers for all
        this.models.forEach(m => {
            if (m.userData.helper) m.userData.helper.visible = false;
        });
        // Show helper for selected
        if (model) {
            this._showHelper(model, true);
            // Update slider
            const slider = document.getElementById('scale-slider');
            if (slider) slider.value = model.scale.x;
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
        if (this.models.length === 0) return [];
        const raycaster = new THREE.Raycaster();
        const mouse = new THREE.Vector2();
        mouse.x = (x / window.innerWidth) * 2 - 1;
        mouse.y = -(y / window.innerHeight) * 2 + 1;
        raycaster.setFromCamera(mouse, this.camera);
        // Intersect all models
        return raycaster.intersectObjects(this.models, true);
    }

    _getModelFromIntersect(intersect) {
        // Traverse up to find the root model object
        let obj = intersect.object;
        while (obj.parent && obj.parent !== this.scene) {
            obj = obj.parent;
        }
        return obj;
    }

    onPointerDown(e) {
        const intersects = this._raycast(e.clientX, e.clientY);
        if (intersects.length > 0) {
            const model = this._getModelFromIntersect(intersects[0]);
            this.selectModel(model);
            this.isDragging = true;
            this.previousMousePosition = { x: e.clientX, y: e.clientY };
        } else {
            // Deselect if clicked empty space? Maybe keep selected for ease of use.
            // this.selectModel(null);
            this.isDragging = false;
        }
    }

    onPointerMove(e) {
        // Cursor
        const intersects = this._raycast(e.clientX, e.clientY);
        document.body.style.cursor = intersects.length > 0 ? 'pointer' : 'default';

        if (!this.isDragging || !this.selectedModel) return;

        // Drag Logic (Camera Plane)
        const factor = 0.005 * (this.camera.position.z / 2);
        
        const deltaX = e.clientX - this.previousMousePosition.x;
        const deltaY = e.clientY - this.previousMousePosition.y;
        
        this.selectedModel.position.x += deltaX * factor;
        this.selectedModel.position.y -= deltaY * factor;
        
        this.previousMousePosition = { x: e.clientX, y: e.clientY };
        
        this._updateHelper(this.selectedModel);
    }

    onPointerUp() {
        this.isDragging = false;
    }

    onWheel(e) {
        e.preventDefault();
        if (!this.selectedModel) return;
        
        const delta = -Math.sign(e.deltaY) * 0.1;
        this._applyScale(delta);
    }

    // Touch Logic
    onTouchStart(e) {
        if (e.touches.length === 1) {
            const touch = e.touches[0];
            const intersects = this._raycast(touch.clientX, touch.clientY);
            if (intersects.length > 0) {
                const model = this._getModelFromIntersect(intersects[0]);
                this.selectModel(model);
                this.isDragging = true;
                this.previousTouch = touch;
            } else {
                this.isDragging = false;
            }
        } else if (e.touches.length === 2) {
            this.isDragging = false;
            this.initialPinchDistance = this._getDistance(e.touches[0], e.touches[1]);
            if (this.selectedModel) this.initialScale = this.selectedModel.scale.x;
        }
    }

    onTouchMove(e) {
        e.preventDefault();
        if (e.touches.length === 1 && this.isDragging && this.selectedModel) {
            const touch = e.touches[0];
            const factor = 0.005 * (this.camera.position.z / 2);
            const dx = (touch.clientX - this.previousTouch.clientX) * factor;
            const dy = -(touch.clientY - this.previousTouch.clientY) * factor; // Invert Y
            
            this.selectedModel.position.x += dx;
            this.selectedModel.position.y += dy;
            this.previousTouch = touch;
            this._updateHelper(this.selectedModel);

        } else if (e.touches.length === 2 && this.selectedModel && this.initialPinchDistance) {
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

    _showHelper(model, visible) {
        if (!model) return;
        if (!model.userData.helper) {
            const helper = new THREE.BoxHelper(model, 0xffff00);
            this.scene.add(helper);
            model.userData.helper = helper;
        }
        model.userData.helper.visible = visible;
    }

    _updateHelper(model) {
        if (model && model.userData.helper) {
            model.userData.helper.update();
        }
    }

    // --- Scaling ---

    _applyScale(delta) {
        if (!this.selectedModel) return;
        const newScale = this.selectedModel.scale.x + delta;
        this.setScale(newScale);
    }

    setScale(val) {
        if (!this.selectedModel) return;
        const clamped = Math.min(Math.max(val, this.config.minScale), this.config.maxScale);
        this.selectedModel.scale.set(clamped, clamped, clamped);
        
        // Sync UI
        const slider = document.getElementById('scale-slider');
        if (slider) slider.value = clamped;
        
        this._updateHelper(this.selectedModel);
    }

    // --- Rotation ---

    rotateTo(angle) {
        if (!this.selectedModel) return;
        this.selectedModel.rotation.y = angle;
        this._updateHelper(this.selectedModel);
    }
    
    rotateBy(axis, angle) {
        if (!this.selectedModel) return;
        // axis: 'x', 'y', 'z'
        this.selectedModel.rotation[axis] += angle;
        this._updateHelper(this.selectedModel);
    }

    // --- UI & Loop ---

    setupUI() {
        // Character Buttons
        document.querySelectorAll('.character-btn').forEach(btn => {
            btn.addEventListener('click', (e) => {
                const target = e.currentTarget;
                
                // If it's the clear button
                if (!target.dataset.model) {
                    this.clearAllModels();
                    return;
                }

                // Load Model
                this.loadModel(target.dataset.model);
            });
        });

        // Add Mode Toggle
        const addModeToggle = document.getElementById('add-mode-toggle');
        if (addModeToggle) {
            addModeToggle.addEventListener('change', (e) => {
                this.toggleAddMode(e.target.checked);
            });
        }

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
        
        this.mixers.forEach(mixer => mixer.update(delta));
        
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
            // Hide helpers
            this.models.forEach(m => {
                if (m.userData.helper) m.userData.helper.visible = false;
            });

            this.renderer.render(this.scene, this.camera);
            ctx.drawImage(this.renderer.domElement, 0, 0, canvas.width, canvas.height);

            // Restore helper for selected
            if (this.selectedModel && this.selectedModel.userData.helper) {
                this.selectedModel.userData.helper.visible = true;
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
window.clearModel = () => arManager.clearAllModels();
window.rotateModel = (angle) => arManager.rotateTo(angle);
window.rotateBy = (axis, angle) => arManager.rotateBy(axis, angle);
