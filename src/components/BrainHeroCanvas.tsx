import React, { useEffect, useRef } from 'react';
import * as THREE from 'three';

export const BrainHeroCanvas: React.FC = () => {
  const containerRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    const container = containerRef.current;
    if (!container) return;

    let width = container.clientWidth || 600;
    let height = container.clientHeight || 580;

    const scene = new THREE.Scene();
    const camera = new THREE.PerspectiveCamera(45, width / height, 0.1, 1000);
    camera.position.set(0, 0, 18);

    const renderer = new THREE.WebGLRenderer({ alpha: true, antialias: true });
    renderer.setSize(width, height);
    renderer.setPixelRatio(Math.min(window.devicePixelRatio || 1, 2));
    container.innerHTML = '';
    container.appendChild(renderer.domElement);

    // Groups
    const masterGroup = new THREE.Group();
    scene.add(masterGroup);

    const brainGroup = new THREE.Group();
    masterGroup.add(brainGroup);

    const nodesGroup = new THREE.Group();
    masterGroup.add(nodesGroup);

    const connectionsGroup = new THREE.Group();
    masterGroup.add(connectionsGroup);

    // 1. Procedural Anatomic Brain Particle Constellation
    const brainParticleCount = 2200;
    const brainGeo = new THREE.BufferGeometry();
    const positions = new Float32Array(brainParticleCount * 3);
    const colors = new Float32Array(brainParticleCount * 3);
    const originalPos = new Float32Array(brainParticleCount * 3);

    const colorCyan = new THREE.Color(0x00f2fe);
    const colorBlue = new THREE.Color(0x3b82f6);
    const colorViolet = new THREE.Color(0x8b5cf6);

    for (let i = 0; i < brainParticleCount; i++) {
      // Dual-hemisphere parametric brain distribution
      const hemisphere = Math.random() > 0.5 ? 1 : -1;
      const u = Math.random();
      const v = Math.random();
      const theta = u * 2.0 * Math.PI;
      const phi = Math.acos(2.0 * v - 1.0);

      // Anatomic lobe modulation
      const r = 4.2 + (Math.sin(theta * 3) * Math.cos(phi * 2) * 0.9) + (Math.random() * 0.4);

      let x = r * Math.sin(phi) * Math.cos(theta) * 0.85 + (hemisphere * 1.0);
      let y = r * Math.cos(phi) * 1.05;
      let z = r * Math.sin(phi) * Math.sin(theta) * 1.35;

      // Temporal lobe curve indentation
      if (y < -0.5 && z > 0) {
        x *= 0.85;
        y *= 0.9;
      }

      positions[i * 3] = x;
      positions[i * 3 + 1] = y;
      positions[i * 3 + 2] = z;

      originalPos[i * 3] = x;
      originalPos[i * 3 + 1] = y;
      originalPos[i * 3 + 2] = z;

      // Mix gradient
      const mixCol = colorCyan.clone().lerp(colorBlue, Math.random() * 0.6).lerp(colorViolet, (y + 4) / 8);
      colors[i * 3] = mixCol.r;
      colors[i * 3 + 1] = mixCol.g;
      colors[i * 3 + 2] = mixCol.b;
    }

    brainGeo.setAttribute('position', new THREE.BufferAttribute(positions, 3));
    brainGeo.setAttribute('color', new THREE.BufferAttribute(colors, 3));

    // Particle texture
    const canvas = document.createElement('canvas');
    canvas.width = 32;
    canvas.height = 32;
    const ctx = canvas.getContext('2d');
    if (ctx) {
      const gradient = ctx.createRadialGradient(16, 16, 0, 16, 16, 16);
      gradient.addColorStop(0, 'rgba(255,255,255,1)');
      gradient.addColorStop(0.3, 'rgba(0,242,254,0.85)');
      gradient.addColorStop(0.7, 'rgba(59,130,246,0.25)');
      gradient.addColorStop(1, 'rgba(0,0,0,0)');
      ctx.fillStyle = gradient;
      ctx.fillRect(0, 0, 32, 32);
    }
    const pTexture = new THREE.CanvasTexture(canvas);

    const particleMat = new THREE.PointsMaterial({
      size: 0.28,
      vertexColors: true,
      map: pTexture,
      transparent: true,
      blending: THREE.AdditiveBlending,
      depthWrite: false
    });

    const brainPoints = new THREE.Points(brainGeo, particleMat);
    brainGroup.add(brainPoints);

    // Internal Synaptic Core lines connecting nearest neighbors
    const lineGeo = new THREE.BufferGeometry();
    const linePositions: number[] = [];
    for (let i = 0; i < 450; i++) {
      const idxA = Math.floor(Math.random() * brainParticleCount);
      const ax = positions[idxA * 3];
      const ay = positions[idxA * 3 + 1];
      const az = positions[idxA * 3 + 2];

      for (let j = 0; j < 3; j++) {
        const idxB = Math.floor(Math.random() * brainParticleCount);
        const bx = positions[idxB * 3];
        const by = positions[idxB * 3 + 1];
        const bz = positions[idxB * 3 + 2];

        const dist = Math.hypot(ax - bx, ay - by, az - bz);
        if (dist < 1.7 && dist > 0.2) {
          linePositions.push(ax, ay, az, bx, by, bz);
        }
      }
    }
    lineGeo.setAttribute('position', new THREE.Float32BufferAttribute(linePositions, 3));
    const lineMat = new THREE.LineBasicMaterial({
      color: 0x00f2fe,
      transparent: true,
      opacity: 0.25,
      blending: THREE.AdditiveBlending
    });
    const brainLines = new THREE.LineSegments(lineGeo, lineMat);
    brainGroup.add(brainLines);

    // Translucent Holographic Contour Shell
    const shellGeo = new THREE.SphereGeometry(4.7, 32, 24);
    shellGeo.scale(0.85, 1.05, 1.28);
    const shellMat = new THREE.MeshPhongMaterial({
      color: 0x00d4ff,
      wireframe: true,
      transparent: true,
      opacity: 0.04,
      blending: THREE.AdditiveBlending
    });
    const shellMesh = new THREE.Mesh(shellGeo, shellMat);
    brainGroup.add(shellMesh);

    // 2. Floating Multimodal Satellite Nodes
    const nodeDefs = [
      { id: 'img', label: 'IMAGE', color: 0x38bdf8, angle: 0, rad: 8.5, y: 3.2 },
      { id: 'speech', label: 'SPEECH', color: 0xa855f7, angle: 1.05, rad: 8.8, y: -2.8 },
      { id: 'ehr', label: 'EHR', color: 0x34d399, angle: 2.1, rad: 9.0, y: 2.2 },
      { id: 'rag', label: 'RAG', color: 0xf59e0b, angle: 3.15, rad: 8.4, y: -2.0 },
      { id: 'llm', label: 'LLM', color: 0x60a5fa, angle: 4.2, rad: 8.7, y: 3.5 },
      { id: 'explain', label: 'EVIDENCE', color: 0x06b6d4, angle: 5.25, rad: 9.2, y: -1.2 }
    ];

    interface ModalNode {
      ring: THREE.Mesh;
      curve: THREE.CatmullRomCurve3;
      pulse: THREE.Mesh;
      progress: number;
    }

    const modalNodes: ModalNode[] = [];

    nodeDefs.forEach((def, index) => {
      const x = Math.cos(def.angle) * def.rad;
      const z = Math.sin(def.angle) * def.rad * 0.7;
      const y = def.y;

      // Glowing core orb
      const orbGeo = new THREE.SphereGeometry(0.55, 24, 24);
      const orbMat = new THREE.MeshPhongMaterial({
        color: def.color,
        emissive: def.color,
        emissiveIntensity: 0.6,
        transparent: true,
        opacity: 0.85
      });
      const orb = new THREE.Mesh(orbGeo, orbMat);
      orb.position.set(x, y, z);
      nodesGroup.add(orb);

      // Outer glass ring
      const ringGeo = new THREE.RingGeometry(0.75, 0.95, 32);
      const ringMat = new THREE.MeshBasicMaterial({
        color: def.color,
        side: THREE.DoubleSide,
        transparent: true,
        opacity: 0.5,
        blending: THREE.AdditiveBlending
      });
      const ring = new THREE.Mesh(ringGeo, ringMat);
      ring.position.set(x, y, z);
      nodesGroup.add(ring);

      // Dynamic Spline curve to brain center
      const curve = new THREE.CatmullRomCurve3([
        new THREE.Vector3(x, y, z),
        new THREE.Vector3(x * 0.55, y * 0.4 + (index % 2 === 0 ? 1 : -1) * 1.5, z * 0.55),
        new THREE.Vector3(0, 0, 0)
      ]);

      const curvePoints = curve.getPoints(50);
      const curveGeo = new THREE.BufferGeometry().setFromPoints(curvePoints);
      const curveMat = new THREE.LineBasicMaterial({
        color: def.color,
        transparent: true,
        opacity: 0.35,
        blending: THREE.AdditiveBlending
      });
      const splineLine = new THREE.Line(curveGeo, curveMat);
      connectionsGroup.add(splineLine);

      // Pulse particle
      const pulseGeo = new THREE.SphereGeometry(0.12, 12, 12);
      const pulseMat = new THREE.MeshBasicMaterial({
        color: 0xffffff,
        transparent: true,
        opacity: 0.9
      });
      const pulse = new THREE.Mesh(pulseGeo, pulseMat);
      connectionsGroup.add(pulse);

      modalNodes.push({
        ring,
        curve,
        pulse,
        progress: Math.random()
      });
    });

    // Lighting
    const ambientLight = new THREE.AmbientLight(0x0a192f, 2.5);
    scene.add(ambientLight);

    const dirLight1 = new THREE.DirectionalLight(0x00f2fe, 3.0);
    dirLight1.position.set(10, 15, 10);
    scene.add(dirLight1);

    const dirLight2 = new THREE.DirectionalLight(0x8b5cf6, 2.0);
    dirLight2.position.set(-10, -10, -10);
    scene.add(dirLight2);

    // Mouse Tracking & Parallax
    let targetRotX = 0;
    let targetRotY = 0;

    const onMouseMove = (e: MouseEvent) => {
      const rect = container.getBoundingClientRect();
      const clientX = e.clientX - rect.left;
      const clientY = e.clientY - rect.top;
      const mouseX = (clientX / rect.width) * 2 - 1;
      const mouseY = -(clientY / rect.height) * 2 + 1;
      targetRotY = mouseX * 0.65;
      targetRotX = -mouseY * 0.45;
    };
    window.addEventListener('mousemove', onMouseMove);

    const onResize = () => {
      if (!container) return;
      width = container.clientWidth || window.innerWidth;
      height = container.clientHeight || 580;
      camera.aspect = width / height;
      camera.updateProjectionMatrix();
      renderer.setSize(width, height);
    };
    window.addEventListener('resize', onResize);

    // Animation loop
    const clock = new THREE.Clock();
    let animId: number;

    const animate = () => {
      animId = requestAnimationFrame(animate);
      const elapsedTime = clock.getElapsedTime();

      // Subtle gentle auto rotation + smooth mouse tilt
      masterGroup.rotation.y += (targetRotY - masterGroup.rotation.y) * 0.04 + 0.0018;
      masterGroup.rotation.x += (targetRotX - masterGroup.rotation.x) * 0.04;

      // Synaptic particle breathing pulsation
      const posAttr = brainGeo.attributes.position as THREE.BufferAttribute;
      const pulseFactor = Math.sin(elapsedTime * 2.2) * 0.06;
      for (let i = 0; i < brainParticleCount; i++) {
        const ox = originalPos[i * 3];
        const oy = originalPos[i * 3 + 1];
        const oz = originalPos[i * 3 + 2];
        const factor = 1.0 + pulseFactor * ((i % 5 === 0) ? 1.5 : 0.8);
        posAttr.setXYZ(i, ox * factor, oy * factor, oz * factor);
      }
      posAttr.needsUpdate = true;

      // Animate Satellite Nodes
      modalNodes.forEach((node) => {
        node.ring.rotation.z += 0.02;
        node.ring.lookAt(camera.position);

        node.progress = (node.progress + 0.009) % 1.0;
        const point = node.curve.getPointAt(node.progress);
        if (point) {
          node.pulse.position.copy(point);
        }
      });

      renderer.render(scene, camera);
    };

    animate();

    return () => {
      cancelAnimationFrame(animId);
      window.removeEventListener('mousemove', onMouseMove);
      window.removeEventListener('resize', onResize);
      renderer.dispose();
      brainGeo.dispose();
      particleMat.dispose();
      lineGeo.dispose();
      lineMat.dispose();
      shellGeo.dispose();
      shellMat.dispose();
    };
  }, []);

  return <div ref={containerRef} className="w-full h-full min-h-[580px] absolute inset-0 z-0 pointer-events-auto bg-transparent" />;
};
