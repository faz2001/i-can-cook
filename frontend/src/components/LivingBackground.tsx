import React, { useEffect, useRef } from 'react';

const VERTEX_SRC = `attribute vec2 a_position;
varying vec2 v_texCoord;
void main() {
  v_texCoord = a_position * 0.5 + 0.5;
  gl_Position = vec4(a_position, 0.0, 1.0);
}`;

const FRAGMENT_SRC = `precision highp float;
varying vec2 v_texCoord;
uniform float u_time;
void main() {
  vec2 uv = v_texCoord;
  vec2 p1 = vec2(0.3 + 0.2 * sin(u_time * 0.1), 0.7 + 0.1 * cos(u_time * 0.12));
  float d1 = length(uv - p1);
  float b1 = smoothstep(0.6, 0.0, d1);
  vec3 c1 = vec3(1.0, 0.6, 0.23);
  vec2 p2 = vec2(0.8 + 0.15 * cos(u_time * 0.2), 0.2 + 0.1 * sin(u_time * 0.18));
  float d2 = length(uv - p2);
  float b2 = smoothstep(0.4, 0.0, d2);
  vec3 c2 = vec3(1.0, 0.31, 0.48);
  vec2 p3 = vec2(0.5 + 0.1 * sin(u_time * 0.3), 0.8 + 0.15 * cos(u_time * 0.25));
  float d3 = length(uv - p3);
  float b3 = smoothstep(0.3, 0.0, d3);
  vec3 c3 = vec3(0.48, 0.23, 0.93);
  vec3 finalColor = mix(vec3(0.99, 0.96, 0.92), c1, b1 * 0.6);
  finalColor = mix(finalColor, c2, b2 * 0.5);
  finalColor = mix(finalColor, c3, b3 * 0.4);
  gl_FragColor = vec4(finalColor, 1.0);
}`;

function createShader(gl: WebGLRenderingContext, type: number, src: string): WebGLShader | null {
  const shader = gl.createShader(type);
  if (!shader) return null;
  gl.shaderSource(shader, src);
  gl.compileShader(shader);
  return shader;
}

/**
 * Ambient animated gradient behind the discovery/home screen. Falls back to a
 * plain CSS gradient (via the wrapper's background classes) if WebGL isn't
 * available -- never throws, never blocks the rest of the page.
 */
export function LivingBackground() {
  const canvasRef = useRef<HTMLCanvasElement>(null);

  useEffect(() => {
    const canvas = canvasRef.current;
    if (!canvas) return;

    const gl = (canvas.getContext('webgl') || canvas.getContext('experimental-webgl')) as WebGLRenderingContext | null;
    if (!gl) return;

    const vs = createShader(gl, gl.VERTEX_SHADER, VERTEX_SRC);
    const fs = createShader(gl, gl.FRAGMENT_SHADER, FRAGMENT_SRC);
    if (!vs || !fs) return;

    const program = gl.createProgram();
    if (!program) return;
    gl.attachShader(program, vs);
    gl.attachShader(program, fs);
    gl.linkProgram(program);
    if (!gl.getProgramParameter(program, gl.LINK_STATUS)) return;
    gl.useProgram(program);

    const buffer = gl.createBuffer();
    gl.bindBuffer(gl.ARRAY_BUFFER, buffer);
    gl.bufferData(gl.ARRAY_BUFFER, new Float32Array([-1, -1, 1, -1, -1, 1, 1, 1]), gl.STATIC_DRAW);
    const positionLoc = gl.getAttribLocation(program, 'a_position');
    gl.enableVertexAttribArray(positionLoc);
    gl.vertexAttribPointer(positionLoc, 2, gl.FLOAT, false, 0, 0);

    const timeLoc = gl.getUniformLocation(program, 'u_time');

    const syncSize = () => {
      const w = window.innerWidth;
      const h = window.innerHeight;
      canvas.width = w;
      canvas.height = h;
      gl.viewport(0, 0, w, h);
    };
    syncSize();
    window.addEventListener('resize', syncSize);

    const reduceMotion = window.matchMedia('(prefers-reduced-motion: reduce)').matches;
    let frame = 0;
    const render = (t: number) => {
      gl.uniform1f(timeLoc, (reduceMotion ? 0 : t) * 0.001);
      gl.drawArrays(gl.TRIANGLE_STRIP, 0, 4);
      if (!reduceMotion) frame = requestAnimationFrame(render);
    };
    render(0);

    return () => {
      window.removeEventListener('resize', syncSize);
      cancelAnimationFrame(frame);
    };
  }, []);

  return (
    <div className="fixed inset-0 z-0 bg-gradient-to-br from-primary-fixed via-background to-tertiary-fixed">
      <canvas ref={canvasRef} className="absolute inset-0 w-full h-full block" />
    </div>
  );
}
