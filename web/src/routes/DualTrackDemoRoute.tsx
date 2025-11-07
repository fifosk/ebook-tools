import React, { useEffect, useState } from "react";
import DualLaneSandbox from '../components/demo/DualLaneSandbox';
import type { TrackTiming } from '../types/timing';

/**
 * Demo route loading generated sample assets (c_demo).
 * Open http://localhost:5173/demo/dual-track after running the pipeline.
 */
export default function DualTrackDemoRoute() {
  const [origTiming, setOrigTiming] = useState<TrackTiming | null>(null);
  const [transTiming, setTransTiming] = useState<TrackTiming | null>(null);

  useEffect(() => {
    Promise.all([
      fetch("/timing/orig/c_demo.timing.json").then((r) => r.json()),
      fetch("/timing/trans/c_demo.timing.json").then((r) => r.json())
    ]).then(([o, t]) => {
      setOrigTiming(o);
      setTransTiming(t);
    });
  }, []);

  if (!origTiming || !transTiming)
    return <div className="p-6 text-gray-600">Loading demo timing data...</div>;

  return (
    <DualLaneSandbox
      origTiming={origTiming}
      transTiming={transTiming}
      origAudioSrc="/audio/orig/c_demo.mp3"
      transAudioSrc="/audio/trans/c_demo.mp3"
    />
  );
}
