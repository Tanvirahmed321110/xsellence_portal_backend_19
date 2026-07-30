(function () {
    function initPortalThreeScene() {
        const host = document.getElementById('portal-three-scene');
        if (!host || !window.THREE) {
            return;
        }

        if (window.innerWidth < 992 || window.matchMedia('(prefers-reduced-motion: reduce)').matches) {
            return;
        }

        document.body.classList.add('portal-scene-active');

        const scene = new THREE.Scene();
        const camera = new THREE.PerspectiveCamera(48, window.innerWidth / window.innerHeight, 0.1, 100);
        camera.position.set(0, 0, 16);

        const renderer = new THREE.WebGLRenderer({
            alpha: true,
            antialias: true,
            powerPreference: 'high-performance',
        });
        renderer.setPixelRatio(Math.min(window.devicePixelRatio || 1, 1.8));
        renderer.setSize(window.innerWidth, window.innerHeight);
        renderer.setClearColor(0x000000, 0);
        host.appendChild(renderer.domElement);

        const ambientLight = new THREE.AmbientLight(0xc4b5fd, 1.35);
        scene.add(ambientLight);

        const pointLight = new THREE.PointLight(0x60a5fa, 2.4, 80, 2);
        pointLight.position.set(8, 6, 10);
        scene.add(pointLight);

        const magentaLight = new THREE.PointLight(0xd946ef, 1.9, 70, 2);
        magentaLight.position.set(-10, -4, 8);
        scene.add(magentaLight);

        const group = new THREE.Group();
        scene.add(group);

        const panels = [];
        const panelGeometry = new THREE.BoxGeometry(4.6, 2.6, 0.16);
        const wireGeometry = new THREE.EdgesGeometry(panelGeometry);
        const panelConfigs = [
            { x: -5.8, y: 2.2, z: -2.8, rx: -0.22, ry: 0.36, color: 0x7c3aed },
            { x: 4.9, y: 1.4, z: -4.4, rx: -0.18, ry: -0.34, color: 0x2563eb },
            { x: -3.4, y: -3.0, z: -5.2, rx: 0.22, ry: 0.3, color: 0x06b6d4 },
            { x: 6.7, y: -2.8, z: -6.0, rx: 0.16, ry: -0.28, color: 0xec4899 },
        ];

        panelConfigs.forEach((config, index) => {
            const panelMaterial = new THREE.MeshPhongMaterial({
                color: 0x170f34,
                emissive: config.color,
                emissiveIntensity: 0.18,
                transparent: true,
                opacity: 0.22,
                shininess: 90,
            });
            const panel = new THREE.Mesh(panelGeometry, panelMaterial);
            panel.position.set(config.x, config.y, config.z);
            panel.rotation.set(config.rx, config.ry, index % 2 ? -0.08 : 0.08);

            const wire = new THREE.LineSegments(
                wireGeometry,
                new THREE.LineBasicMaterial({
                    color: config.color,
                    transparent: true,
                    opacity: 0.82,
                })
            );
            panel.add(wire);
            group.add(panel);
            panels.push(panel);
        });

        const starGeometry = new THREE.BufferGeometry();
        const starCount = 180;
        const starPositions = new Float32Array(starCount * 3);
        for (let index = 0; index < starCount; index += 1) {
            const stride = index * 3;
            starPositions[stride] = (Math.random() - 0.5) * 34;
            starPositions[stride + 1] = (Math.random() - 0.5) * 22;
            starPositions[stride + 2] = -Math.random() * 20;
        }
        starGeometry.setAttribute('position', new THREE.BufferAttribute(starPositions, 3));
        const stars = new THREE.Points(
            starGeometry,
            new THREE.PointsMaterial({
                color: 0xe9d5ff,
                size: 0.06,
                transparent: true,
                opacity: 0.7,
            })
        );
        group.add(stars);

        const floorGeometry = new THREE.PlaneGeometry(46, 28, 22, 16);
        const floorMaterial = new THREE.MeshBasicMaterial({
            color: 0x312e81,
            wireframe: true,
            transparent: true,
            opacity: 0.12,
        });
        const floor = new THREE.Mesh(floorGeometry, floorMaterial);
        floor.rotation.x = -1.16;
        floor.position.set(0, -6.6, -7.2);
        group.add(floor);

        let frameId = null;
        let mouseX = 0;
        let mouseY = 0;
        const clock = new THREE.Clock();

        function resizeScene() {
            camera.aspect = window.innerWidth / window.innerHeight;
            camera.updateProjectionMatrix();
            renderer.setSize(window.innerWidth, window.innerHeight);
        }

        function handlePointerMove(event) {
            mouseX = (event.clientX / window.innerWidth - 0.5) * 2;
            mouseY = (event.clientY / window.innerHeight - 0.5) * 2;
        }

        function animate() {
            const elapsed = clock.getElapsedTime();

            group.rotation.y += (mouseX * 0.12 - group.rotation.y) * 0.03;
            group.rotation.x += (-mouseY * 0.06 - group.rotation.x) * 0.03;

            panels.forEach((panel, index) => {
                panel.position.y += Math.sin(elapsed * 0.8 + index * 0.65) * 0.0035;
                panel.rotation.z = Math.sin(elapsed * 0.5 + index) * 0.08;
            });

            stars.rotation.y = elapsed * 0.03;
            floor.position.z = -7.2 + Math.sin(elapsed * 0.35) * 0.18;

            renderer.render(scene, camera);
            frameId = window.requestAnimationFrame(animate);
        }

        window.addEventListener('resize', resizeScene);
        window.addEventListener('pointermove', handlePointerMove, { passive: true });
        animate();

        window.addEventListener('beforeunload', function () {
            if (frameId) {
                window.cancelAnimationFrame(frameId);
            }
            renderer.dispose();
            panelGeometry.dispose();
            wireGeometry.dispose();
            floorGeometry.dispose();
            starGeometry.dispose();
        });
    }

    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', initPortalThreeScene);
    } else {
        initPortalThreeScene();
    }
})();
