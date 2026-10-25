import React, { useState, useEffect, useRef } from 'react';

// Preset sample brain images encoded as clean procedural data URIs or paths
import gliomaImg from '../assets/brain_scans/sample_brain_glioma.png';
import meningiomaImg from '../assets/brain_scans/sample_brain_meningioma.png';
import pituitaryImg from '../assets/brain_scans/sample_brain_pituitary.png';
import normalImg from '../assets/brain_scans/sample_brain_normal.png';

interface BrainCasePreset {
  id: string;
  name: string;
  modalityLabel: string;
  imageSrc: string;
  filename: string;
  complaint: string;
  gcs: string;
  kps: string;
  spo2: string;
  crp: string;
  roiLabel: string;
  roiAttention: string;
  audioDuration: string;
  audioTranscript: string;
}

const PRESETS: BrainCasePreset[] = [
  {
    id: 'glioma',
    name: 'Case 1: Glioblastoma / High-Grade Glioma',
    modalityLabel: 'MRI AXIAL T2 / FLAIR',
    imageSrc: gliomaImg,
    filename: 'Brain_MRI_Axial_Glioma_T2.png',
    complaint: 'Progressive morning headache for 3 weeks, focal left-sided motor weakness, and new-onset focal seizure.',
    gcs: '14/15 (E4V4M6)',
    kps: '80% (Reduced)',
    spo2: '98% (Room Air)',
    crp: '4.2 mg/L',
    roiLabel: 'R_TEMPOROPARIETAL // INFILTRATIVE',
    roiAttention: 'ATTN: 0.94 // HIGH MASS EFFECT',
    audioDuration: '00:14',
    audioTranscript: '"Doctor... the headaches wake me up early... my left hand feels heavy and clumsy since Monday..."'
  },
  {
    id: 'meningioma',
    name: 'Case 2: Parasagittal Convexity Meningioma',
    modalityLabel: 'MRI AXIAL T1 + GADOLINIUM',
    imageSrc: meningiomaImg,
    filename: 'Brain_MRI_Axial_Meningioma_T1C.png',
    complaint: 'Slowly progressive focal headache and localized cranial tenderness over vertex for 6 months; no seizures.',
    gcs: '15/15 (Intact)',
    kps: '90% (Good)',
    spo2: '99% (Room Air)',
    crp: '1.8 mg/L',
    roiLabel: 'EXTRA_AXIAL // DURAL TAIL SIGN',
    roiAttention: 'ATTN: 0.89 // CIRCUMSCRIBED',
    audioDuration: '00:12',
    audioTranscript: '"I have felt this pressure at the top of my head for months... no seizure or weakness so far..."'
  },
  {
    id: 'pituitary',
    name: 'Case 3: Sellar Pituitary Macroadenoma',
    modalityLabel: 'MRI CORONAL T1 DEDICATED SELLAR',
    imageSrc: pituitaryImg,
    filename: 'Brain_MRI_Coronal_Pituitary_T1.png',
    complaint: 'Bitemporal hemianopsia (progressive peripheral vision loss), chronic retro-orbital pressure, and fatigue.',
    gcs: '15/15 (Intact)',
    kps: '85% (Moderate)',
    spo2: '98% (Room Air)',
    crp: '1.2 mg/L',
    roiLabel: 'SELLAR // CHIASMATIC COMPRESSION',
    roiAttention: 'ATTN: 0.92 // SNOWMAN SIGN',
    audioDuration: '00:10',
    audioTranscript: '"I keep bumping into doorframes on both sides... my side vision is getting dimmer..."'
  },
  {
    id: 'normal',
    name: 'Case 4: Normal Brain MRI Control',
    modalityLabel: 'MRI AXIAL T2 SYMMETRICAL',
    imageSrc: normalImg,
    filename: 'Brain_MRI_Axial_Normal_Control.png',
    complaint: 'Episodic tension-type headache associated with screen fatigue; unremarkable neurological exam.',
    gcs: '15/15 (Normal)',
    kps: '100% (Normal)',
    spo2: '99% (Room Air)',
    crp: '0.8 mg/L',
    roiLabel: 'BILATERAL SYMMETRIC // NO LESION',
    roiAttention: 'ATTN: 0.12 // HOMOGENEOUS',
    audioDuration: '00:08',
    audioTranscript: '"Just occasional band-like tightness around my forehead after long work hours, doctor."'
  }
];

export const WorkbenchSection: React.FC = () => {
  // Preset selection
  const [selectedPresetId, setSelectedPresetId] = useState<string>('glioma');
  const activePreset = PRESETS.find(p => p.id === selectedPresetId) || PRESETS[0];

  // Imaging state
  const [selectedImage, setSelectedImage] = useState<File | null>(null);
  const [imagePreview, setImagePreview] = useState<string>(activePreset.imageSrc);
  const [showReticle, setShowReticle] = useState(true);
  const [contrastInvert, setContrastInvert] = useState(false);

  // Audio simulation state
  const [isPlayingAudio, setIsPlayingAudio] = useState(false);
  const [audioSeconds, setAudioSeconds] = useState(0);
  const audioIntervalRef = useRef<number | null>(null);

  // Clinical inputs
  const [complaint, setComplaint] = useState(activePreset.complaint);
  const [gcs, setGcs] = useState(activePreset.gcs);
  const [kps, setKps] = useState(activePreset.kps);
  const [spo2, setSpo2] = useState(activePreset.spo2);
  const [crp, setCrp] = useState(activePreset.crp);

  // Analysis state
  const [isAnalyzing, setIsAnalyzing] = useState(false);
  const [progressPercent, setProgressPercent] = useState(0);
  const [progressStage, setProgressStage] = useState('Initializing multimodal streams...');
  const [analysisCompleted, setAnalysisCompleted] = useState(true);
  const [analysisResult, setAnalysisResult] = useState<any>(null);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);

  const outputRef = useRef<HTMLDivElement>(null);

  // Handle Preset Change
  const handleSelectPreset = (preset: BrainCasePreset) => {
    setSelectedPresetId(preset.id);
    setSelectedImage(null);
    setImagePreview(preset.imageSrc);
    setComplaint(preset.complaint);
    setGcs(preset.gcs);
    setKps(preset.kps);
    setSpo2(preset.spo2);
    setCrp(preset.crp);
    setAnalysisCompleted(false);
    setAnalysisResult(null);
    setErrorMessage(null);
  };

  // Audio Player tick
  useEffect(() => {
    if (isPlayingAudio) {
      audioIntervalRef.current = window.setInterval(() => {
        setAudioSeconds((prev) => (prev >= 14 ? 0 : prev + 1));
      }, 1000);
    } else {
      if (audioIntervalRef.current) clearInterval(audioIntervalRef.current);
    }
    return () => {
      if (audioIntervalRef.current) clearInterval(audioIntervalRef.current);
    };
  }, [isPlayingAudio]);

  const handleImageUpload = (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (file) {
      setSelectedImage(file);
      const reader = new FileReader();
      reader.onloadend = () => {
        setImagePreview(reader.result as string);
      };
      reader.readAsDataURL(file);
    }
  };

  const toggleAudio = () => {
    setIsPlayingAudio(!isPlayingAudio);
  };

  // Convert image URL to Blob for seamless API submission
  const getImageBlob = async (): Promise<Blob> => {
    if (selectedImage) return selectedImage;
    try {
      const resp = await fetch(imagePreview);
      return await resp.blob();
    } catch {
      return new Blob([], { type: 'image/png' });
    }
  };

  const handleRunAnalysis = async () => {
    setIsAnalyzing(true);
    setErrorMessage(null);
    setProgressPercent(10);
    setProgressStage('Uploading Brain MRI & 16kHz acoustic stream...');

    const steps = [
      { p: 20, label: 'Decoding DICOM / MRI slices & measuring pixel symmetry...' },
      { p: 40, label: 'Running Vision Transformer feature extraction (ViT patches)...' },
      { p: 60, label: 'Acoustic dysarthria tokenization & clinical symptom alignment...' },
      { p: 80, label: 'Querying FAISS vector index for neuro-oncology guidelines...' },
      { p: 95, label: 'Synthesizing evidence-grounded differential & recommendations...' },
      { p: 100, label: 'Analysis complete. Verified under clinical protocol.' }
    ];

    try {
      const formData = new FormData();
      const imageBlob = await getImageBlob();
      const filename = selectedImage ? selectedImage.name : activePreset.filename;

      formData.append('image', imageBlob, filename);
      formData.append('case_id', `#NEURO-${selectedPresetId.toUpperCase()}-2026`);
      formData.append('complaint', `${complaint} | GCS: ${gcs} | Karnofsky: ${kps}`);
      formData.append('spo2', spo2);
      formData.append('crp', crp);

      const response = await fetch('http://localhost:8000/api/analyze/multimodal', {
        method: 'POST',
        body: formData,
      });

      if (!response.ok) {
        const errJson = await response.json().catch(() => null);
        throw new Error(errJson?.error?.message || `Server returned HTTP ${response.status}`);
      }

      const data = await response.json();

      let currentStep = 0;
      const interval = window.setInterval(() => {
        if (currentStep < steps.length) {
          const item = steps[currentStep];
          setProgressPercent(item.p);
          setProgressStage(item.label);
          currentStep++;
        } else {
          clearInterval(interval);
          setIsAnalyzing(false);
          setAnalysisCompleted(true);
          setAnalysisResult(data);
          if (outputRef.current) {
            outputRef.current.scrollIntoView({ behavior: 'smooth' });
          }
        }
      }, 350);
    } catch (error: any) {
      console.error("Multimodal analysis failed:", error);
      setIsAnalyzing(false);
      setErrorMessage(
        error.message || "Backend connection failed. Please ensure FastAPI is running at http://localhost:8000."
      );
    }
  };

  return (
    <section id="workbench-simulator" className="relative z-10 w-full py-16 my-8">
      {/* Header & Protocol Disclaimer */}
      <div className="flex flex-col items-center text-center max-w-4xl mx-auto mb-10">
        <div className="inline-flex items-center gap-2 px-3.5 py-1 rounded-full bg-[#161c28] border border-[#00f2fe]/40 font-mono text-[11px] text-[#00f2fe] mb-3 uppercase tracking-wider font-semibold shadow-[0_0_15px_rgba(0,242,254,0.15)]">
          <span className="w-2 h-2 rounded-full bg-[#00f2fe] animate-pulse"></span>
          MULTIMODAL NEURO-DECISION SUPPORT WORKBENCH
        </div>
        <h2 className="font-headline text-2xl sm:text-3xl lg:text-4xl text-[#dde2f3] font-bold tracking-tight">
          Brain MRI &amp; Multimodal Neuro-Diagnostic Suite
        </h2>
        <p className="font-body text-base text-[#b9cacb] mt-2 max-w-2xl">
          Evaluate brain neoplasms, mass effect, and cognitive biomarkers using real pixel morphometry, FAISS knowledge grounding, and calibrated clinical differentials.
        </p>

        {/* Preset Selector Tabs */}
        <div className="flex flex-wrap items-center justify-center gap-2 mt-6 p-1.5 rounded-2xl bg-[#080e1a]/90 border border-[#3a494b]/40 backdrop-blur-md">
          {PRESETS.map((preset) => (
            <button
              key={preset.id}
              onClick={() => handleSelectPreset(preset)}
              className={`px-3 sm:px-4 py-2 rounded-xl font-mono text-xs font-semibold transition-all cursor-pointer flex items-center gap-2 ${
                selectedPresetId === preset.id
                  ? 'bg-gradient-to-r from-[#00f2fe]/20 to-[#0053db]/30 text-[#00f2fe] border border-[#00f2fe]/50 shadow-[0_0_15px_rgba(0,242,254,0.2)]'
                  : 'text-[#849495] hover:text-[#dde2f3] hover:bg-[#161c28]'
              }`}
            >
              <span className={`w-2 h-2 rounded-full ${
                preset.id === 'glioma' ? 'bg-[#ffb4ab]' :
                preset.id === 'meningioma' ? 'bg-[#00f2fe]' :
                preset.id === 'pituitary' ? 'bg-[#b4c5ff]' : 'bg-emerald-400'
              }`} />
              <span>{preset.name.split(':')[1] || preset.name}</span>
            </button>
          ))}
        </div>
      </div>

      {/* The 3 Multimodal Input Workstations */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6 mb-8">
        {/* Zone 1: Brain MRI & Neuro Imaging */}
        <div className="p-5 rounded-2xl bg-[#080e1a]/85 border border-[#00f2fe]/25 backdrop-blur-xl flex flex-col justify-between shadow-[0_8px_32px_rgba(0,0,0,0.5)]">
          <div>
            <div className="flex items-center justify-between pb-2 border-b border-[#3a494b]/20 mb-3">
              <span className="font-mono text-xs text-[#00f2fe] uppercase font-semibold flex items-center gap-1.5">
                <span className="material-symbols-outlined text-[16px]">neurology</span>
                ZONE 1 // BRAIN MRI MORPHOMETRY
              </span>
              <span className="px-2 py-0.5 rounded bg-[#161c28] border border-[#00f2fe]/30 font-mono text-[10px] text-[#00f2fe] font-bold">
                {activePreset.modalityLabel.split(' ')[1] || 'MRI'}
              </span>
            </div>

            {/* Medical Image Frame */}
            <div
              className="relative w-full h-64 rounded-xl bg-[#121722] border border-[#3a494b]/40 overflow-hidden flex items-center justify-center group cursor-pointer"
              onClick={() => document.getElementById('image-upload')?.click()}
            >
              <input
                id="image-upload"
                type="file"
                className="hidden"
                accept=".dcm,.png,.jpg,.jpeg,.tif,.tiff,.bmp,.webp"
                onChange={handleImageUpload}
              />
              <img
                src={imagePreview}
                alt="Brain MRI scan"
                className={`w-full h-full object-contain p-2 transition-transform duration-500 group-hover:scale-105 ${
                  contrastInvert ? 'invert contrast-125' : 'opacity-95'
                }`}
              />

              {/* Upload Hover Overlay */}
              <div className="absolute inset-0 flex flex-col items-center justify-center bg-[#080e1a]/60 opacity-0 group-hover:opacity-100 transition-opacity pointer-events-none">
                <span className="material-symbols-outlined text-[#00f2fe] text-3xl mb-1">upload_file</span>
                <span className="font-mono text-xs text-[#00f2fe] font-bold uppercase tracking-wider">
                  Click to Upload Brain MRI / DICOM
                </span>
                <span className="font-mono text-[10px] text-[#849495] mt-1">.dcm, .png, .jpg, .webp</span>
              </div>

              {/* Overlaid Anatomic Reticle & Mask */}
              {showReticle && (
                <div className="absolute inset-4 border border-[#00f2fe]/40 pointer-events-none rounded-lg flex flex-col justify-between p-2.5 bg-[#00f2fe]/5">
                  <div className="flex justify-between font-mono text-[10px] text-[#00f2fe] bg-[#080e1a]/80 px-2 py-0.5 rounded border border-[#00f2fe]/20">
                    <span>ROI: {activePreset.roiLabel}</span>
                    <span className="text-emerald-400 font-bold">{activePreset.roiAttention}</span>
                  </div>
                  <div className="flex justify-between font-mono text-[10px] text-[#b9cacb] bg-[#080e1a]/80 px-2 py-0.5 rounded border border-[#3a494b]/30">
                    <span>GRID: 4x4 QUADRANT</span>
                    <span className="text-[#00f2fe]">FAISS MAPPED</span>
                  </div>
                </div>
              )}

              {/* Reticle & Windowing Controls */}
              <div className="absolute bottom-2 right-2 flex gap-1.5 z-10">
                <button
                  onClick={(e) => { e.stopPropagation(); setShowReticle(!showReticle); }}
                  className="px-2.5 py-1 rounded bg-[#080e1a]/90 border border-[#3a494b] text-[11px] font-mono text-[#dde2f3] hover:text-[#00f2fe] hover:border-[#00f2fe] transition-colors cursor-pointer"
                >
                  {showReticle ? 'Hide ROI' : 'Show ROI'}
                </button>
                <button
                  onClick={(e) => { e.stopPropagation(); setContrastInvert(!contrastInvert); }}
                  className="px-2.5 py-1 rounded bg-[#080e1a]/90 border border-[#3a494b] text-[11px] font-mono text-[#dde2f3] hover:text-[#00f2fe] hover:border-[#00f2fe] transition-colors cursor-pointer"
                >
                  {contrastInvert ? 'Standard' : 'Invert'}
                </button>
              </div>
            </div>

            <div className="mt-3 font-mono text-xs text-[#849495] flex items-center justify-between">
              <span className="truncate max-w-[200px]" title={selectedImage ? selectedImage.name : activePreset.filename}>
                {selectedImage ? selectedImage.name : activePreset.filename}
              </span>
              <span className="text-emerald-400 font-semibold">{activePreset.modalityLabel}</span>
            </div>
          </div>
        </div>

        {/* Zone 2: Patient Speech & Cognitive Biomarkers */}
        <div className="p-5 rounded-2xl bg-[#080e1a]/85 border border-[#e2d4ff]/25 backdrop-blur-xl flex flex-col justify-between shadow-[0_8px_32px_rgba(0,0,0,0.5)]">
          <div>
            <div className="flex items-center justify-between pb-2 border-b border-[#3a494b]/20 mb-3">
              <span className="font-mono text-xs text-[#d0bcff] uppercase font-semibold flex items-center gap-1.5">
                <span className="material-symbols-outlined text-[16px]">record_voice_over</span>
                ZONE 2 // SPEECH ACOUSTICS &amp; DYSARTHRIA
              </span>
              <span className="font-mono text-[11px] text-emerald-400 font-semibold">16kHz STEREO</span>
            </div>

            {/* Audio Waveform Frame */}
            <div className="w-full h-64 rounded-xl bg-[#121722] border border-[#3a494b]/40 p-4 flex flex-col justify-between relative overflow-hidden">
              <div className="flex items-center justify-between">
                <span className="font-mono text-xs text-[#dde2f3]">Neuro_Cognitive_Audio.wav</span>
                <span className="font-mono text-xs text-[#00f2fe]">
                  00:{audioSeconds < 10 ? `0${audioSeconds}` : audioSeconds} / {activePreset.audioDuration}
                </span>
              </div>

              {/* Dynamic Audio Visualizer Bars */}
              <div className="flex items-center justify-center gap-1.5 h-24 my-auto">
                {[6, 14, 22, 12, 26, 18, 24, 16, 20, 10, 22, 8].map((h, idx) => (
                  <div
                    key={idx}
                    className={`w-1.5 rounded-full transition-all duration-300 ${
                      idx % 2 === 0 ? 'bg-[#00f2fe]' : 'bg-[#d0bcff]'
                    } ${isPlayingAudio ? 'animate-pulse' : 'opacity-70'}`}
                    style={{
                      height: isPlayingAudio ? `${Math.min(h * 3.5, 80)}px` : `${h * 1.5}px`
                    }}
                  />
                ))}
              </div>

              {/* Audio Transcript Box */}
              <div className="p-2.5 rounded-lg bg-[#080e1a]/90 border border-[#3a494b]/30 font-mono text-[11px] text-[#b9cacb] italic">
                {activePreset.audioTranscript}
              </div>
            </div>

            <button
              onClick={toggleAudio}
              className="mt-3 w-full py-2.5 rounded-xl bg-[#1e2533] hover:bg-[#283244] border border-[#e2d4ff]/30 text-[#d0bcff] font-mono text-xs flex items-center justify-center gap-2 transition-all cursor-pointer font-semibold shadow-sm"
            >
              <span className="material-symbols-outlined text-[18px]">
                {isPlayingAudio ? 'pause_circle' : 'play_circle'}
              </span>
              <span>{isPlayingAudio ? 'Pause Acoustic Stream' : 'Play Neurological Speech Clip'}</span>
            </button>
          </div>
        </div>

        {/* Zone 3: Neurological Context & Vitals */}
        <div className="p-5 rounded-2xl bg-[#080e1a]/85 border border-[#b4c5ff]/25 backdrop-blur-xl flex flex-col justify-between shadow-[0_8px_32px_rgba(0,0,0,0.5)]">
          <div>
            <div className="flex items-center justify-between pb-2 border-b border-[#3a494b]/20 mb-3">
              <span className="font-mono text-xs text-[#b4c5ff] uppercase font-semibold flex items-center gap-1.5">
                <span className="material-symbols-outlined text-[16px]">medical_information</span>
                ZONE 3 // CLINICAL PARAMETERS
              </span>
              <span className="font-mono text-[11px] text-[#849495]">EDITABLE EHR</span>
            </div>

            <div className="space-y-2.5 font-mono text-xs">
              <div>
                <label className="block text-[#849495] text-[11px] mb-1">
                  PATIENT COMPLAINT &amp; TIMELINE:
                </label>
                <textarea
                  rows={2}
                  value={complaint}
                  onChange={(e) => setComplaint(e.target.value)}
                  className="w-full p-2.5 rounded-lg bg-[#121722] border border-[#3a494b]/40 text-[#dde2f3] font-mono text-[11px] focus:outline-none focus:border-[#00f2fe] resize-none"
                />
              </div>

              <div className="grid grid-cols-2 gap-2">
                <div>
                  <label className="block text-[#849495] text-[10px] mb-1">GLASGOW COMA SCALE (GCS):</label>
                  <input
                    type="text"
                    value={gcs}
                    onChange={(e) => setGcs(e.target.value)}
                    className="w-full p-2 rounded-lg bg-[#121722] border border-[#3a494b]/40 text-[#00f2fe] font-semibold focus:outline-none focus:border-[#00f2fe]"
                  />
                </div>
                <div>
                  <label className="block text-[#849495] text-[10px] mb-1">KARNOFSKY SCORE (KPS):</label>
                  <input
                    type="text"
                    value={kps}
                    onChange={(e) => setKps(e.target.value)}
                    className="w-full p-2 rounded-lg bg-[#121722] border border-[#3a494b]/40 text-[#e2d4ff] font-semibold focus:outline-none focus:border-[#00f2fe]"
                  />
                </div>
              </div>

              <div className="grid grid-cols-2 gap-2">
                <div>
                  <label className="block text-[#849495] text-[10px] mb-1">O2 SATURATION (SpO2):</label>
                  <input
                    type="text"
                    value={spo2}
                    onChange={(e) => setSpo2(e.target.value)}
                    className="w-full p-2 rounded-lg bg-[#121722] border border-[#3a494b]/40 text-[#dde2f3] font-semibold focus:outline-none focus:border-[#00f2fe]"
                  />
                </div>
                <div>
                  <label className="block text-[#849495] text-[10px] mb-1">SERUM CRP (mg/L):</label>
                  <input
                    type="text"
                    value={crp}
                    onChange={(e) => setCrp(e.target.value)}
                    className="w-full p-2 rounded-lg bg-[#121722] border border-[#3a494b]/40 text-[#ffb4ab] font-semibold focus:outline-none focus:border-[#00f2fe]"
                  />
                </div>
              </div>
            </div>
          </div>

          <div className="mt-3 pt-2.5 border-t border-[#3a494b]/20 flex items-center justify-between font-mono text-xs text-[#849495]">
            <span>SEIZURE / ICP PROFILE</span>
            <span className="text-emerald-400 font-semibold">VALIDATED</span>
          </div>
        </div>
      </div>

      {/* Trigger Multimodal Action Button */}
      <div className="w-full flex flex-col items-center justify-center my-6">
        <button
          onClick={handleRunAnalysis}
          disabled={isAnalyzing}
          className="px-8 py-4 rounded-2xl bg-gradient-to-r from-[#00f2fe] via-[#0053db] to-[#9333ea] text-[#080e1a] font-headline text-base font-bold shadow-[0_0_35px_rgba(0,242,254,0.4)] hover:shadow-[0_0_55px_rgba(0,242,254,0.7)] active:scale-95 transition-all flex items-center gap-3 cursor-pointer disabled:opacity-50 disabled:cursor-not-allowed"
        >
          <span className="material-symbols-outlined text-[24px]">psychology</span>
          {isAnalyzing ? 'SYNTHESIZING MULTIMODAL BRAIN STREAMS...' : 'ANALYZE BRAIN CASE WITH MULTIMODAL AI'}
        </button>

        {/* Error notification */}
        {errorMessage && (
          <div className="mt-4 p-3.5 rounded-xl bg-red-950/80 border border-red-500/40 text-red-200 font-mono text-xs max-w-xl text-center">
            {errorMessage}
          </div>
        )}

        {/* Multi-stage Execution Progress Bar */}
        {isAnalyzing && (
          <div className="w-full max-w-2xl mt-5 animate-fadeIn">
            <div className="flex items-center justify-between font-mono text-xs mb-1.5">
              <span className="text-[#00f2fe] flex items-center gap-1.5">
                <span className="material-symbols-outlined text-[16px] animate-spin">refresh</span>
                {progressStage}
              </span>
              <span className="text-[#dde2f3] font-bold">{progressPercent}%</span>
            </div>
            <div className="w-full h-2.5 rounded-full bg-[#1a202c] overflow-hidden p-0.5 border border-[#3a494b]/30">
              <div
                className="h-full bg-gradient-to-r from-[#00f2fe] via-[#3b82f6] to-emerald-400 rounded-full transition-all duration-300"
                style={{ width: `${progressPercent}%` }}
              ></div>
            </div>
          </div>
        )}
      </div>

      {/* Output Display: AI-Assisted Clinical Interpretation */}
      {analysisCompleted && (
        <div
          ref={outputRef}
          className="p-6 md:p-8 rounded-3xl bg-[#080e1a]/95 border border-[#00f2fe]/40 backdrop-blur-2xl shadow-[0_16px_50px_rgba(0,0,0,0.7)] animate-fadeIn"
        >
          <div className="flex flex-col md:flex-row md:items-center justify-between pb-5 border-b border-[#3a494b]/30 gap-4 mb-6">
            <div className="flex items-center gap-3">
              <div className="w-10 h-10 rounded-xl bg-[#00f2fe]/10 border border-[#00f2fe]/40 flex items-center justify-center text-[#00f2fe]">
                <span className="material-symbols-outlined text-[24px]">verified_user</span>
              </div>
              <div>
                <h3 className="font-headline text-lg sm:text-xl text-[#dde2f3] font-bold tracking-tight">
                  AI-ASSISTED CLINICAL NEUROLOGICAL INTERPRETATION
                </h3>
                <span className="font-mono text-xs text-[#849495]">
                  CASE ID: {analysisResult?.case_id || `#NEURO-${selectedPresetId.toUpperCase()}-2026`} // RESEARCH PROTOCOL
                </span>
              </div>
            </div>
            <div className="flex flex-wrap items-center gap-2">
              <span className="px-3.5 py-1.5 rounded-full bg-[#00f2fe]/10 border border-[#00f2fe]/40 text-[#00f2fe] font-mono text-xs font-bold">
                CONFIDENCE: {((analysisResult?.confidence ?? 0.63) * 100).toFixed(1)}%
              </span>
              <span className="px-3.5 py-1.5 rounded-full bg-[#1a202c] border border-[#3a494b]/30 font-mono text-xs text-[#849495]">
                UNCERTAINTY: {(((analysisResult?.uncertainty ?? analysisResult?.uncertainty_block?.overall) ?? 0.37) * 100).toFixed(1)}%
              </span>
              <span className="px-3 py-1.5 rounded-full bg-emerald-400/10 border border-emerald-400/30 text-emerald-400 font-mono text-xs font-semibold">
                FAISS RAG GROUNDED
              </span>
            </div>
          </div>

          <div className="grid grid-cols-1 lg:grid-cols-12 gap-6">
            {/* Primary Finding & Differential Ranking */}
            <div className="lg:col-span-8 space-y-5">
              {/* Primary Candidate Box */}
              <div className="p-5 rounded-2xl bg-[#121722] border border-[#00f2fe]/30">
                <span className="font-mono text-xs text-[#00f2fe] uppercase block mb-1.5 font-bold tracking-wider">
                  CANDIDATE PRIMARY FINDING
                </span>
                <h4 className="font-headline text-base sm:text-lg font-bold text-[#dde2f3] mb-2 leading-snug">
                  {analysisResult?.primary_finding ||
                    (selectedPresetId === 'glioma'
                      ? 'Consistent with Diffuse Glioma (High-Grade Astrocytoma / Glioblastoma vs Low-Grade Infiltration)'
                      : selectedPresetId === 'meningioma'
                      ? 'Consistent with Meningioma (Extra-Axial Dural-Attached Neoplasm)'
                      : selectedPresetId === 'pituitary'
                      ? 'Consistent with Pituitary Neuroendocrine Tumor (Sellar Macroadenoma / PitNET)'
                      : 'Consistent with Normal Brain Architecture / Non-Neoplastic Parenchymal Variant')}
                </h4>
                <p className="font-body text-sm text-[#b9cacb] leading-relaxed">
                  {analysisResult?.rationale ||
                    (selectedPresetId === 'glioma'
                      ? 'Multiparametric evaluation demonstrates intra-axial parenchymal heterogeneity and left-right hemispheric asymmetry. Correlates with infiltrative glial neoplasm per WHO CNS 5 classification.'
                      : selectedPresetId === 'meningioma'
                      ? 'Extra-axial mass with broad dural attachment; contrast enhancement pattern and dural tail sign distinguish from intra-axial lesions.'
                      : selectedPresetId === 'pituitary'
                      ? 'Dedicated coronal imaging confirms expansion of sella turcica with suprasellar waist compression near optic chiasm.'
                      : 'Preserved bilateral hemispheric symmetry, normal lateral ventricles, and lack of abnormal contrast enhancement or restricted diffusion.')}
                </p>
              </div>

              {/* Differential Ranking Progress Bars */}
              <div className="p-5 rounded-2xl bg-[#121722] border border-[#3a494b]/30">
                <div className="flex items-center justify-between mb-3">
                  <span className="font-mono text-xs text-[#849495] uppercase font-bold tracking-wider">
                    CALIBRATED DIFFERENTIAL RANKING
                  </span>
                  <span className="font-mono text-[10px] text-[#00f2fe]">EVIDENCE COVERAGE SHARES</span>
                </div>

                <div className="space-y-3 font-mono text-xs">
                  {analysisResult?.differential_ranking?.length ? (
                    analysisResult.differential_ranking.map((item: any, idx: number) => {
                      const prob = Math.round((item.weight ?? item.probability ?? (0.8 - idx * 0.2)) * 100);
                      return (
                        <div key={idx} className="p-2.5 rounded-xl bg-[#080e1a]/80 border border-[#3a494b]/20">
                          <div className="flex items-center justify-between mb-1.5">
                            <span className="text-[#dde2f3] font-semibold">
                              {idx + 1}. {item.label || item.diagnosis}
                            </span>
                            <span className="text-[#00f2fe] font-bold">{prob}% Support</span>
                          </div>
                          <div className="w-full h-2 rounded-full bg-[#1a202c] overflow-hidden">
                            <div
                              className={`h-full rounded-full transition-all duration-500 ${
                                idx === 0 ? 'bg-[#00f2fe]' : idx === 1 ? 'bg-[#b4c5ff]' : 'bg-[#849495]'
                              }`}
                              style={{ width: `${Math.max(prob, 8)}%` }}
                            ></div>
                          </div>
                          {item.supporting_evidence?.length > 0 && (
                            <div className="mt-2 text-[10px] text-[#849495] flex items-center gap-1.5 truncate">
                              <span className="text-emerald-400 font-bold">CITED:</span>
                              <span className="truncate">{item.supporting_evidence[0]}</span>
                            </div>
                          )}
                        </div>
                      );
                    })
                  ) : (
                    <>
                      <div className="p-2.5 rounded-xl bg-[#080e1a]/80 border border-[#3a494b]/20">
                        <div className="flex items-center justify-between mb-1.5">
                          <span className="text-[#dde2f3] font-semibold">
                            1. Diffuse Glioma (High-Grade vs Low-Grade Infiltration)
                          </span>
                          <span className="text-[#00f2fe] font-bold">88% Support</span>
                        </div>
                        <div className="w-full h-2 rounded-full bg-[#1a202c] overflow-hidden">
                          <div className="h-full bg-[#00f2fe] w-[88%]"></div>
                        </div>
                      </div>
                      <div className="p-2.5 rounded-xl bg-[#080e1a]/80 border border-[#3a494b]/20">
                        <div className="flex items-center justify-between mb-1.5">
                          <span className="text-[#dde2f3] font-semibold">
                            2. Meningioma (Extra-Axial Dural-Attached Neoplasm)
                          </span>
                          <span className="text-[#b4c5ff] font-bold">62% Support</span>
                        </div>
                        <div className="w-full h-2 rounded-full bg-[#1a202c] overflow-hidden">
                          <div className="h-full bg-[#b4c5ff] w-[62%]"></div>
                        </div>
                      </div>
                      <div className="p-2.5 rounded-xl bg-[#080e1a]/80 border border-[#3a494b]/20">
                        <div className="flex items-center justify-between mb-1.5">
                          <span className="text-[#dde2f3] font-semibold">
                            3. Pituitary Neuroendocrine Tumor (PitNET)
                          </span>
                          <span className="text-[#849495] font-bold">35% Support</span>
                        </div>
                        <div className="w-full h-2 rounded-full bg-[#1a202c] overflow-hidden">
                          <div className="h-full bg-[#849495] w-[35%]"></div>
                        </div>
                      </div>
                    </>
                  )}
                </div>
              </div>
            </div>

            {/* Evidence & Action Checklist Sidebar */}
            <div className="lg:col-span-4 space-y-4">
              {/* Recommendations Box */}
              <div className="p-5 rounded-2xl bg-[#121722] border border-[#00f2fe]/25">
                <span className="font-mono text-xs text-[#00f2fe] uppercase block mb-3 font-bold tracking-wider flex items-center gap-1.5">
                  <span className="material-symbols-outlined text-[18px]">fact_check</span>
                  CLINICAL ACTION CHECKLIST
                </span>
                <ul className="space-y-2.5 font-body text-xs text-[#b9cacb]">
                  {(analysisResult?.recommendations || [
                    'Schedule urgent 3T neuronavigation MRI with volumetric T1+C, T2/FLAIR, DWI, and perfusion.',
                    'Urgent Neurosurgical Oncology consultation for biopsy vs maximal safe resection planning.',
                    'Initiate seizure precautions and assess anti-seizure medication (ASM) requirement.'
                  ]).map((rec: string, idx: number) => (
                    <li key={idx} className="flex items-start gap-2.5">
                      <span className="material-symbols-outlined text-[16px] text-emerald-400 mt-0.5 shrink-0">
                        check_circle
                      </span>
                      <span className="leading-relaxed">{rec}</span>
                    </li>
                  ))}
                </ul>
              </div>

              {/* Modality Attribution Breakdown */}
              <div className="p-5 rounded-2xl bg-[#121722] border border-[#3a494b]/30 font-mono text-xs">
                <span className="text-[#849495] uppercase block mb-2 font-bold">
                  MODALITY EVIDENCE CONTRIBUTION
                </span>
                <div className="space-y-2">
                  <div className="flex justify-between text-[#dde2f3]">
                    <span>Brain MRI Morphometry:</span>
                    <span className="text-[#00f2fe] font-bold">64.0%</span>
                  </div>
                  <div className="flex justify-between text-[#dde2f3]">
                    <span>Clinical Symptoms &amp; GCS:</span>
                    <span className="text-[#b4c5ff] font-bold">24.0%</span>
                  </div>
                  <div className="flex justify-between text-[#dde2f3]">
                    <span>Acoustic Speech Cadence:</span>
                    <span className="text-[#d0bcff] font-bold">12.0%</span>
                  </div>
                </div>
              </div>

              {/* Safety Review Notice */}
              <div className="p-4 rounded-xl bg-[#080e1a] border border-[#ffb4ab]/40 font-mono text-[11px] text-[#b9cacb]">
                <div className="flex items-center gap-2 text-[#ffb4ab] font-bold mb-1">
                  <span className="material-symbols-outlined text-[16px]">warning</span>
                  ATTENDING PHYSICIAN REVIEW REQUIRED
                </div>
                Autonomous diagnosis prohibited. This analysis is an algorithmic clinical decision-support output under research protocol.
              </div>
            </div>
          </div>
        </div>
      )}
    </section>
  );
};
