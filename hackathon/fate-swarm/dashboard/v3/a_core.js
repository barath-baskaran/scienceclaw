// ===== W-TOOL dashboard v3: core helpers (pure functions; testable headless) =====
var DATA = window.__DATA__ || {};
var EPM = DATA.endpoints || {};
var FATE = ['logkow','water_solubility','vapor_pressure','henry','boiling_point','melting_point','koc','bcf','logkoa','koh_gas','pka_acidic','pka_basic'];
var HAZ = ['rat_oral_ld50','er_active','er_potency','ar_active','ar_potency'];
function $(id){return document.getElementById(id);}
function esc(s){return String(s==null?'':s).replace(/[&<>"']/g,function(c){return {'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c];});}
function num(x){return x!=null && typeof x==='number' && isFinite(x);}
function f(x,d){if(!num(x))return '–';d=(d==null?2:d);return (+x).toFixed(d);}
function sig(x,n){if(!num(x))return '–';if(x===0)return '0';var a=Math.abs(x);n=n||2;
  if(a>=1e5||a<1e-3)return x.toExponential(n-1).replace('e+','×10^').replace('e-','×10^-');
  return (+x.toPrecision(n)).toString();}
function epLabel(ep){return (EPM[ep]&&EPM[ep].label)||ep;}
function epWhat(ep){return (EPM[ep]&&EPM[ep].what)||'';}
function epUnits(ep){return (EPM[ep]&&EPM[ep].units)||'';}
function pct(x){return num(x)?Math.round(100*x)+'%':'–';}

// ---- plain-unit conversions (shown next to the model's own log units; formula stated)
function natural(ep,v,mw){
  if(!num(v))return null;
  switch(ep){
  case 'water_solubility': return mw?{t:sig(Math.pow(10,v)*mw*1000,2)+' mg/L',how:'10^value × MW × 1000'}:null;
  case 'vapor_pressure': return {t:sig(Math.pow(10,v)*133.322,2)+' Pa',how:'10^value mmHg × 133.322'};
  case 'henry': return {t:sig(Math.pow(10,v)*101325,2)+' Pa·m³/mol',how:'10^value atm·m³/mol × 101325'};
  case 'koc': return {t:sig(Math.pow(10,v),2)+' L/kg',how:'10^value'};
  case 'bcf': return {t:sig(Math.pow(10,v),2)+' L/kg',how:'10^value'};
  case 'logkow': return {t:'Kow ≈ '+sig(Math.pow(10,v),2),how:'10^value'};
  case 'logkoa': return {t:'Koa ≈ '+sig(Math.pow(10,v),2),how:'10^value'};
  case 'koh_gas': var k=Math.pow(10,v);var hrs=Math.LN2/(k*1.5e6)/3600;
    return {t:'half-life in air ≈ '+(hrs<48?sig(hrs,2)+' h':sig(hrs/24,2)+' days'),how:'ln2 / (k × [OH]); [OH] = 1.5×10^6 molecules/cm³ (24-h average assumed; EPI AOPWIN uses 1.5×10^6 over a 12-h day, i.e. 2× longer)'};
  case 'rat_oral_LD50': return mw?{t:sig(Math.pow(10,v)*mw,2)+' mg/kg body weight',how:'10^value mmol/kg × MW'}:null;
  default: return null;}
}

// ---- domain flag: never colour alone (symbol + words)
function domTag(d,fam,kind){
  if(d==='na')return '<span class="tag t-na">not assessed</span><div class="small">spectral match '+f(fam)+'; similarity did not predict error for spectra, so no novelty call is made</div>';
  var t=({'in':['t-in','● familiar'],'edge':['t-edge','▲ somewhat new'],'out':['t-out','✖ new to the model']})[d];
  if(!t)return '<span class="tag t-na">? unknown</span>';
  var k=kind==='spectral_cosine'?'spectral similarity to nearest training spectrum':'structural similarity (Tanimoto, 0–1) to nearest training compound';
  return '<span class="tag '+t[0]+'" title="'+esc(k)+': '+f(fam)+'">'+t[1]+'</span><div class="small">'+(kind==='spectral_cosine'?'spectral match ':'similarity ')+f(fam)+'</div>';
}

// ---- plain names for model features (top drivers)
function featName(n){
  var s=String(n), m;
  if((m=s.match(/^(?:morgan|ecfp|fp|mfp|m)_?(?:cnt_?|bit_?)?(\d+)$/i)))return 'substructure fingerprint bit '+m[1];
  if((m=s.match(/^maccs_(\d+)$/i)))return 'MACCS substructure key '+m[1];
  s=s.replace(/^d_/,'').replace(/^rd_/,'');
  var map={MolLogP:'Crippen logP (computed lipophilicity)',MolWt:'molecular weight',HeavyAtomMolWt:'heavy-atom molecular weight',TPSA:'polar surface area',
    NumHDonors:'H-bond donors',NumHAcceptors:'H-bond acceptors',NumRotatableBonds:'rotatable bonds',RingCount:'ring count',NumAromaticRings:'aromatic rings',
    FractionCSP3:'fraction of sp3 carbons',qed:'drug-likeness score (QED)',MaxPartialCharge:'largest partial charge (Gasteiger)',MinPartialCharge:'most negative partial charge (Gasteiger)',
    LabuteASA:'approximate surface area',BertzCT:'structural complexity (Bertz)',HallKierAlpha:'shape/flexibility index (Hall-Kier alpha)',MolMR:'molar refractivity'};
  if(map[s])return map[s];
  if((m=s.match(/^PEOE_VSA(\d+)$/)))return 'surface area with partial charge in band '+m[1];
  if((m=s.match(/^SlogP_VSA(\d+)$/)))return 'surface area with lipophilicity contribution in band '+m[1];
  if((m=s.match(/^SMR_VSA(\d+)$/)))return 'surface area with polarisability contribution in band '+m[1];
  if((m=s.match(/^EState_VSA(\d+)$/)))return 'surface area with E-state in band '+m[1];
  if((m=s.match(/^VSA_EState(\d+)$/)))return 'E-state sum in surface-area band '+m[1];
  if((m=s.match(/^fr_(.+)$/)))return 'count of '+m[1].replace(/_/g,' ')+' groups';
  if((m=s.match(/^phys_(.+)$/))||(m=s.match(/^(dipole|sasa|q_|rg_|e_resid|cpsa|homo|lumo|gap)(.*)$/i))){
    var p=s.replace(/^phys_/,'');
    var pm={dipole_D:'dipole moment (AIMNet2)',sasa_A2:'solvent-accessible surface area (3D)',sasa_polar_frac:'polar fraction of 3D surface',rg_A:'radius of gyration (3D size)',
      q_O_min_e:'most negative oxygen charge (AIMNet2)',q_N_min_e:'most negative nitrogen charge (AIMNet2)',q_max_e:'largest atomic charge (AIMNet2)',q_min_e:'most negative atomic charge (AIMNet2)',
      e_resid_per_atom_eV:'energy residual per atom (AIMNet2)',asphericity_A2:'3D asphericity',max_extent_A:'3D length'};
    return pm[p]||('physics descriptor: '+p.replace(/_/g,' '));}
  if((m=s.match(/^(pos|neg)_(?:int_)?(.+)$/)))return (m[1]==='pos'?'positive-mode':'negative-mode')+' spectrum: '+m[2].replace(/_/g,' ');
  if((m=s.match(/^meta_(.+)$/)))return 'spectrum metadata: '+m[1].replace(/_/g,' ');
  if((m=s.match(/^sp_(.+)$/)))return 'spectrum feature: '+m[1].replace(/_/g,' ');
  return s.replace(/_/g,' ');
}

// ---- model flags in plain language
var FLAGTXT=[
 [/physics_computed_but_this_model_cannot_use_it/,'Quantum-chemistry descriptors were computed, but this model can only use them for chemicals in its precomputed table, so it used its structure-only version.'],
 [/physics_rejected_by_model/,'Quantum-chemistry descriptors were computed, but the model could not accept them (input mismatch), so it used its structure-only version.'],
 [/pka_weak_acid_only|^out_of_domain_nn/,''],
 [/^no_physics$/,'Structure-only model version used (no quantum-chemistry descriptors).'],
 [/physics_at_inference/,'Quantum-chemistry descriptors were computed for this structure just now.'],
 [/out_of_domain|OUT_OF_DOMAIN|FAR_FROM/,'Less similar training data: expect larger errors. The likely range already allows for this (it was calibrated on equally unfamiliar test chemicals).'],
 [/OUTSIDE_TRAINING_DESCRIPTOR_RANGE/,'Size or lipophilicity (heavy-atom count or Crippen logP) is outside the 1st-99th percentile of this property\'s training chemicals. Similarity cannot see this (e.g. long chains look "familiar"); on such test chemicals errors were larger and ranges held less often (W-MODEL v5_main/size_domain.csv).'],
 [/ELEMENT_NOT_IN_TRAINING/,'Contains an element never seen in this property\'s training data: expect larger errors.'],
 [/^CAVEAT:/,''],[/PHYSICS_COMPUTED_AT_INFERENCE|physics computed at inference by CPU/,'Quantum-chemistry descriptors were computed for this structure just now (CPU AIMNet2).'],
 [/PHYSICS_FROM_STEREOISOMER/,'Quantum-chemistry descriptors taken from a stereoisomer (they are not stereo-aware).'],
 [/ce_approx/,'Collision energy was approximated from the metadata.'],
 [/spectrum_given_but_not_used/,'The spectrum you gave was not used by this model.'],
 [/screening_level/,'Screening-level estimate only.'],
 [/spectrum_unusable/,'The spectrum could not be used (too few valid peaks or missing metadata).']];
function flagText(fl){var out=[];(fl||[]).forEach(function(x){for(var i=0;i<FLAGTXT.length;i++){if(FLAGTXT[i][0].test(x)){if(FLAGTXT[i][1]&&out.indexOf(FLAGTXT[i][1])<0)out.push(FLAGTXT[i][1]);return;}}out.push('model flag: '+x);});return out;}

// ---- range bar: interval (box), estimate (filled diamond), EPI (hollow circle), measured (×). Shapes, not colours.
function rangeBar(ep,c,epiV,truthV){
  var sc=(EPM[ep]&&EPM[ep].scale)||null; var lo=c.interval[0],hi=c.interval[1],v=c.value;
  var a=sc?sc[0]:Math.min(lo,v), b=sc?sc[1]:Math.max(hi,v);
  [lo,hi,v,epiV,truthV].forEach(function(x){if(num(x)){a=Math.min(a,x);b=Math.max(b,x);}});
  if(b-a<1e-9){b=a+1;}
  var W=150,H=18,P=5; function X(x){return P+(W-2*P)*(x-a)/(b-a);}
  var s='<svg class="rb" width="'+W+'" height="'+H+'" viewBox="0 0 '+W+' '+H+'" role="img" aria-label="range '+f(lo)+' to '+f(hi)+'">';
  s+='<line x1="'+P+'" y1="9" x2="'+(W-P)+'" y2="9" stroke="#bbb" stroke-width="1"/>';
  s+='<rect x="'+X(lo).toFixed(1)+'" y="4" width="'+Math.max(2,X(hi)-X(lo)).toFixed(1)+'" height="10" fill="#cfe3f1" stroke="#0072B2" stroke-width="1"/>';
  if(num(epiV))s+='<circle cx="'+X(epiV).toFixed(1)+'" cy="9" r="4" fill="#fff" stroke="#000" stroke-width="1.5"><title>EPI Suite '+f(epiV)+'</title></circle>';
  if(num(truthV))s+='<path d="M'+(X(truthV)-4).toFixed(1)+' 5 l8 8 m0 -8 l-8 8" stroke="#b34700" stroke-width="2"><title>measured '+f(truthV)+'</title></path>';
  s+='<path d="M'+X(v).toFixed(1)+' 3 l5 6 l-5 6 l-5 -6 z" fill="#000"><title>estimate '+f(v)+'</title></path>';
  return s+'</svg>';
}

// ---- interval sentence: nominal level ALWAYS next to empirical coverage
function covCell(c){return covCell0(c)+(num(c.width_ratio_to_typical)&&c.width_ratio_to_typical>1.5?'<div class="small"><span class="tag t-edge">▲ unusually wide</span> this range is '+f(c.width_ratio_to_typical,1)+'× the typical width in this band (typical '+sig((c.coverage||{}).median_width,3)+'): the model is unsure about this molecule, and the coverage figure was measured on typical ranges</div>':'');}
function wilson(p,n){if(!num(p)||!num(n)||n<=0)return null;var z=1.96,d=1+z*z/n,c=(p+z*z/(2*n))/d,h=z*Math.sqrt(p*(1-p)/n+z*z/(4*n*n))/d;return [Math.max(0,c-h),Math.min(1,c+h)];}
function wtxt(c){var cv=c.coverage||{},w=wilson(cv.empirical_coverage,cv.n);return w?'<div class="small">95% Wilson interval on that figure: '+pct(w[0])+'–'+pct(w[1])+' (n='+cv.n+')</div>':'';}
function covCell0(c){return covCell1(c)+wtxt(c);}
function covCell1(c){
  var cv=c.coverage||{}, lvl=c.interval_level;
  if(!num(cv.n)&&num(cv.empirical_coverage))return '<b>'+pct(cv.empirical_coverage)+'</b> <span class="small">(n not available)</span><div class="small">(nominal '+pct(lvl)+')</div>';
  if(num(cv.n)&&cv.n<30)return '<span class="tag t-na">too few to check</span><div class="small">only '+cv.n+' test chemicals in this novelty band (nominal '+pct(lvl)+'; observed '+pct(cv.empirical_coverage)+')</div>';
  if(!num(cv.empirical_coverage))return '<span class="tag t-na">not validated</span><div class="small">nominal '+pct(lvl)+'; no test coverage found for this model and novelty band</div>';
  var ok=cv.empirical_coverage>=lvl-0.05;
  return '<b>'+pct(cv.empirical_coverage)+' held (n='+(cv.n==null?'?':cv.n)+')</b> <span class="small"> — share of the test chemicals this new whose measured value fell inside their range</span><div class="small">(nominal '+pct(lvl)+(ok?'':' — <b>held less often than claimed</b>')+')</div>';
}
