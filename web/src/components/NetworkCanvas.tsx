"use client";

import { useEffect, useRef } from "react";
import * as THREE from "three";

const NODE_COUNT = 56;
const LINK_DIST = 2.45;
const COLOR = 0x005032;

/**
 * Quiet Three.js constellation — signal nodes + thin links.
 * Sits behind the hero; pauses when tab is hidden or reduced-motion is on.
 */
export function NetworkCanvas() {
  const mountRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    const mount = mountRef.current;
    if (!mount) return;

    const reduceMotion = window.matchMedia(
      "(prefers-reduced-motion: reduce)",
    ).matches;

    const width = mount.clientWidth;
    const height = mount.clientHeight;
    if (width < 8 || height < 8) return;

    const scene = new THREE.Scene();
    const camera = new THREE.PerspectiveCamera(42, width / height, 0.1, 100);
    camera.position.set(0, 0.15, 6.6);

    const renderer = new THREE.WebGLRenderer({
      antialias: true,
      alpha: true,
      powerPreference: "low-power",
    });
    renderer.setPixelRatio(Math.min(window.devicePixelRatio, 2));
    renderer.setSize(width, height, false);
    renderer.setClearColor(0x000000, 0);
    mount.appendChild(renderer.domElement);

    const group = new THREE.Group();
    group.position.x = 1.35;
    scene.add(group);

    // Seeded-ish layout for a stable “network” shape
    const positions: THREE.Vector3[] = [];
    for (let i = 0; i < NODE_COUNT; i++) {
      const t = i / NODE_COUNT;
      const angle = t * Math.PI * 2.7 + Math.sin(i * 1.7) * 0.4;
      const radius = 1.1 + (i % 7) * 0.28 + Math.sin(i * 0.9) * 0.15;
      const x = Math.cos(angle) * radius * 1.35;
      const y = Math.sin(angle * 0.85) * radius * 0.75 + Math.cos(i) * 0.2;
      const z = Math.sin(i * 0.55) * 0.9;
      positions.push(new THREE.Vector3(x, y, z));
    }

    const nodeGeo = new THREE.BufferGeometry().setFromPoints(positions);
    const nodeMat = new THREE.PointsMaterial({
      color: COLOR,
      size: 0.078,
      sizeAttenuation: true,
      transparent: true,
      opacity: 0.72,
      depthWrite: false,
    });
    const nodes = new THREE.Points(nodeGeo, nodeMat);
    group.add(nodes);

    const linkPositions: number[] = [];
    for (let i = 0; i < NODE_COUNT; i++) {
      for (let j = i + 1; j < NODE_COUNT; j++) {
        if (positions[i].distanceTo(positions[j]) < LINK_DIST) {
          linkPositions.push(
            positions[i].x,
            positions[i].y,
            positions[i].z,
            positions[j].x,
            positions[j].y,
            positions[j].z,
          );
        }
      }
    }
    const linkGeo = new THREE.BufferGeometry();
    linkGeo.setAttribute(
      "position",
      new THREE.Float32BufferAttribute(linkPositions, 3),
    );
    const linkMat = new THREE.LineBasicMaterial({
      color: COLOR,
      transparent: true,
      opacity: 0.28,
      depthWrite: false,
    });
    const links = new THREE.LineSegments(linkGeo, linkMat);
    group.add(links);

    let frame = 0;
    let running = !reduceMotion;
    const clock = new THREE.Clock();

    const onResize = () => {
      const w = mount.clientWidth;
      const h = mount.clientHeight;
      if (w < 8 || h < 8) return;
      camera.aspect = w / h;
      camera.updateProjectionMatrix();
      renderer.setSize(w, h, false);
    };

    const onVisibility = () => {
      running = document.visibilityState === "visible" && !reduceMotion;
      if (running) clock.start();
    };

    window.addEventListener("resize", onResize);
    document.addEventListener("visibilitychange", onVisibility);
    const ro = new ResizeObserver(onResize);
    ro.observe(mount);

    const tick = () => {
      frame = requestAnimationFrame(tick);
      if (!running) {
        renderer.render(scene, camera);
        return;
      }
      const t = clock.getElapsedTime();
      group.rotation.y = t * 0.07;
      group.rotation.x = Math.sin(t * 0.18) * 0.08;
      nodeMat.opacity = 0.62 + Math.sin(t * 0.6) * 0.12;
      linkMat.opacity = 0.24 + Math.sin(t * 0.45) * 0.06;
      renderer.render(scene, camera);
    };

    // Static first paint even with reduced motion
    renderer.render(scene, camera);
    if (!reduceMotion) tick();
    else running = false;

    return () => {
      cancelAnimationFrame(frame);
      ro.disconnect();
      window.removeEventListener("resize", onResize);
      document.removeEventListener("visibilitychange", onVisibility);
      nodeGeo.dispose();
      nodeMat.dispose();
      linkGeo.dispose();
      linkMat.dispose();
      renderer.dispose();
      if (renderer.domElement.parentNode === mount) {
        mount.removeChild(renderer.domElement);
      }
    };
  }, []);

  return (
    <div
      ref={mountRef}
      className="pointer-events-none absolute inset-0 h-full w-full translate-x-[8%] opacity-95 sm:translate-x-[12%] [&_canvas]:h-full [&_canvas]:w-full"
      aria-hidden
    />
  );
}
