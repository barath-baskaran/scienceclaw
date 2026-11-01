// ===== rendering a prediction record (pure: record -> HTML string) =====
function epiOf(rec,ep,c){
  if(ep.indexOf('pka')===0)return {v:null,html:'<span class="small">no EPI comparator (EPI Suite has no pKa module)</span>'};
  if(HAZ.indexOf(ep)>=0)return {v:null,html:'<span class="small">no EPI comparator for this endpoint</span>'};
  var e=(c&&c.epi)||(((rec.epi||{}).values||{})[ep]);
  if(e&&num(e.value))return {v:e.value,html:'<b class="nospin">'+f(e.value)+'</b><div class="small">'+esc(e.module||'')+'</div>'};
  var st=(rec.epi||{}).status;
  var why={not_fetched:'not fetched (offline result)',fetch_failed:'EPI web service not reachable',identity_mismatch:'EPI returned a different structure — not shown',ok:'EPI gave no value'}[st]||('not available'+(st?' ('+st+')':''));
  return {v:null,html:'<span class="small">'+esc(why)+'</span>'};
}
function truthOf(rec,ep){var t=(rec.truth||{})[ep];return t&&num(t.value)?t.value:null;}

function idBox(rec){
  var i=rec.input||{}, h='<div class="panel"><div class="idbox">';
  h+='<div class="mol" aria-label="structure drawing">'+(i.svg||(i.smiles?'<div class="small" style="padding:30px">structure drawing unavailable</div>':'<div class="small" style="padding:30px">no structure (spectrum only)</div>'))+'</div><div>';
  h+='<h3>'+(i.smiles?'What the tool understood':'Spectrum-only query')+'</h3><dl class="kv">';
  if(i.smiles){
    h+='<dt>You entered</dt><dd class="mono">'+esc(i.smiles)+'</dd>';
    if(i.canonical_smiles&&i.canonical_smiles!==i.smiles)h+='<dt>Canonical</dt><dd class="mono">'+esc(i.canonical_smiles)+'</dd>';
    h+='<dt>Formula · MW</dt><dd>'+esc(i.formula||'–')+' · '+f(i.mw,2)+' g/mol</dd><dt>InChIKey</dt><dd class="mono">'+esc(i.inchikey||'–')+'</dd>';
    if(i.n_fragments>1)h+='<dt>Components</dt><dd>'+i.n_fragments+' (a salt or mixture as drawn)</dd>';
  } else if(i.spectrum){var m=i.spectrum.meta||{};
    h+='<dt>Precursor m/z</dt><dd>'+f(m.precursor_mz,4)+' ('+esc(m.adduct||'?')+', '+esc(m.polarity||m.ionization_mode||'?')+')</dd><dt>Peaks</dt><dd>'+((i.spectrum.mz||[]).length)+'</dd><dt>Collision energy</dt><dd>'+(num(m.collision_energy_eV)?f(m.collision_energy_eV,0)+' eV':'unknown')+'</dd>';}
  var sp=rec.species;
  if(sp&&sp.species_class&&(sp.species_class!=='neutralisable'||rec.parent_note))h+='<dt>Species</dt><dd>'+esc(sp.plain||sp.species_class)+'</dd>';
  if(rec.parent_note)h+='<dt>Note</dt><dd>'+esc(rec.parent_note)+'</dd>';
  var ph=rec.physics;
  if(ph&&i.smiles){var pt={ok:'computed ('+f(ph.seconds,0)+' s'+(ph.converged?', converged':'')+(ph.source==='gpu_table'?', from the precomputed table':'')+')',
     skipped_by_user:'not requested (tick the box to compute, ~1 min)',failed:'FAILED — '+(ph.detail||''),not_available:'unavailable — '+(ph.detail||''),unavailable_new_structure:'unavailable — '+(ph.detail||'')}[ph.status]||ph.status;
    if(ph.status==='ok'&&ph.source==='cpu_relax')pt=(num(ph.n_rotatable)&&ph.n_rotatable>=4?'physics approximate (conformer-dependent): ':'physics computed at inference: ')+pt;
    h+='<dt>Quantum chemistry</dt><dd>'+esc(pt)+((ph.notes||[]).length?'<div class="small">▲ '+ph.notes.map(esc).join('<br>')+'</div>':'')+(ph.status==='ok'&&ph.source!=='gpu_table'?'<div class="small">CPU/GPU parity: '+esc(ph.parity||'see About')+'</div>':'')+'</dd>';}
  if(num(rec.seconds_total))h+='<dt>Time</dt><dd>'+f(rec.seconds_total,1)+' s</dd>';
  if(rec.label)h+='<dt>Example</dt><dd>'+esc(rec.label)+'</dd>';
  h+='</dl>';
  if((rec.errors||[]).length)h+='<div class="alert err"><b>Problems</b>'+rec.errors.map(esc).join('<br>')+'</div>';
  return h+'</div></div></div>';
}

var GASP={vapor_pressure:'vapour pressure',henry:'air–water split (Henry constant)',boiling_point:'boiling point',logkoa:'octanol–air split',koh_gas:'reaction with OH radicals in air'};
function plainUndef(ep,c){var sub=String(c.subtype||c.reason||'');
  if(c.category==='A2'||/q003_sulfonate/.test(sub)){
    if(GASP[ep])return 'Not physically meaningful: a sulfonate/sulfate is a strong-acid salt that stays ionised and does not evaporate, so it has no '+GASP[ep]+'. Treated like a permanent ion (expert note Q-003). This is not missing data.';
    return 'Not physically meaningful: the neutral acid is essentially absent at any environmental pH, so a measured Kow would only be an apparent ratio that depends on the salt and the water. Treated like a permanent ion (expert note Q-003). This is not missing data.';}
  if(c.category==='B'||/unpopulated|inner_salt|neutral form/i.test(sub)){
    return 'Defined only for a neutral form that hardly exists at environmental pH: a measured value would be an apparent distribution ratio (D) or an ion-pair value, not this property.';}
  if(/permanent_charge|permanent cation|permanent anion|zwitterion/i.test(sub)){
    if(GASP[ep])return 'Not defined: a permanently charged ion cannot evaporate, so it has no '+GASP[ep]+'. This is not missing data.';
    if(ep==='logkow')return 'Not defined: Kow describes the neutral molecule, and this ion has no neutral form. This is not missing data.';}
  if(/miscible/i.test(sub))return 'Not defined: the liquid mixes with water in all proportions, so there is no finite solubility.';
  if(/no_hydrogen/i.test(sub))return 'Not defined: there is no hydrogen atom to give up.';
  return 'Not defined for this species. This is not missing data.';}
function undefRow(ep,c,ncol){
  var heur=(c.kind==='not_applicable'), nass=(c.kind==='not_assessed');
  var head=c.headline||(heur?'No ionisable site found (heuristic)':'Not physically defined for this compound class');
  var tag='<span class="tag t-und">⊘ '+esc(head)+'</span>'+(heur||nass||c.model_gap?'':'<div style="margin-top:4px"><b>'+esc(plainUndef(ep,c))+'</b></div>');
  var txt=nass?'▲ No number: the model was trained only on carbon-containing chemicals, so it has no basis here and no test of how well it would do. This says nothing about whether the property exists.':c.model_gap?'▲ This property is defined (for the neat neutral form) but the frozen model gives no value for this class. That is a gap in the model, not missing physics; EPI Suite\'s value, if shown elsewhere, is not checked for this class.':heur?'No acidic/basic group of the kinds checked was found, so no pKa is reported. This is a rule of thumb, not a proof.':
      'No number is given because this quantity does not exist for this kind of species. It is not missing data, and it is not a very wide range.';
  return '<tr class="main"><td class="prop"><b>'+esc(epLabel(ep))+'</b><span class="hint">'+esc(epWhat(ep))+'</span></td><td colspan="'+(ncol-1)+'" class="undef">'+tag+
    '<div class="small" style="margin-top:4px">'+txt+'</div><details><summary>Why (full reasoning)</summary><div class="small"><b>Why:</b> '+esc(c.reason||'')+' <span class="small">(rule: '+esc(c.rule_source||'')+')</span></div></details></td></tr>';
}
function caveatHtml(c,short){
  var cv=c.caveat; var out='';
  if(cv)out+='<div class="small" style="margin-top:3px"><span class="tag t-edge">▲ '+esc(cv.headline)+'</span>'+(short?'':'<div>'+esc(cv.reason)+'</div>')+'</div>';
  if(c.note_plain)out+='<div class="small" style="margin-top:3px"><span class="tag t-edge">▲ extrapolation</span>'+(short?'':'<div>'+esc(c.note_plain)+'</div>')+'</div>';
  return out;
}

function detailHtml(ep,c,rec){
  var h='<div class="dgrid">';
  // what drove it
  var a=c.attribution_blocks||{}; h+='<div><h4>What drove this estimate</h4>';
  if(num(a.structure)){
    h+='<div class="bar" role="img" aria-label="structure '+pct(a.structure)+', physics '+pct(a.physics)+', spectrum '+pct(a.spectra)+'"><span class="k-s" style="width:'+(100*a.structure)+'%"></span><span class="k-p" style="width:'+(100*(a.physics||0))+'%"></span><span class="k-m" style="width:'+(100*(a.spectra||0))+'%"></span></div>';
    h+='<div class="legend"><span><span class="sw k-s"></span>structure '+pct(a.structure)+'</span><span><span class="sw k-p"></span>quantum chemistry '+pct(a.physics||0)+'</span><span><span class="sw k-m"></span>spectrum '+((rec.input||{}).has_spectrum||c.familiarity_kind==='spectral_cosine'?pct(a.spectra||0):'not supplied')+'</span></div>';
  } else h+='<div class="small">The model did not report how much each input contributed.</div>';
  var tf=c.top_features||[];
  if(tf.length){h+='<div class="small">Largest single contributions (SHAP, in '+esc(epUnits(ep))+'):</div><ul class="drv">'+tf.map(function(t){
     return '<li>'+(t.shap>=0?'▲ raises':'▼ lowers')+' by '+f(Math.abs(t.shap),2)+': '+esc(featName(t.name))+' <span class="small mono">'+esc(t.name)+'</span></li>';}).join('')+'</ul>';
     if(c.top_features_note)h+='<div class="small">'+esc(c.top_features_note)+'</div>';}
  else if(c.top_features_note)h+='<div class="small">'+esc(c.top_features_note)+'</div>';
  h+='</div>';
  // how good
  var sk=c.skill_naive||{}, o=sk.overall||{}, b=sk.this_bin||{};
  h+='<div><h4>How good is this model on test chemicals</h4>';
  var lf=sk.leak_free||{};
  if(num(o.rmse_pct_naive)||num(b.rmse_pct_naive)){
    h+='<div class="small">Error as % of a naive guess (always predicting the training average; 100% = no skill, lower is better):</div>';
    if(num(lf.rmse_pct_naive))h+='<div><b>'+Math.round(lf.rmse_pct_naive)+'%</b> on leak-free test chemicals (nothing similar in training; n='+lf.n+')</div>';
    if(c.interval&&num(lf.empirical_coverage)&&lf.n>=30){var lw=wilson(lf.empirical_coverage,lf.n),nomv=c.interval_level;
      h+='<div class="small">Range on those leak-free chemicals: held for '+pct(lf.empirical_coverage)+' (n='+lf.n+'; 95% Wilson '+pct(lw[0])+'–'+pct(lw[1])+') at nominal '+pct(nomv)+((num(nomv)&&lw[1]<nomv)?' <b>▲ below nominal: on unfamiliar chemistry the range is too narrow</b>':'')+'</div>';}
    else if(lf.too_few)h+='<div class="small">leak-free test set too small to report (n='+lf.n+')</div>';
    if(num(b.rmse_pct_naive))h+='<div><b>'+Math.round(b.rmse_pct_naive)+'%</b> on test chemicals as new to the model as this one (n='+b.n+(b.n<30?', few':'')+')</div>';
    if(num(o.rmse_pct_naive))h+='<div class="small">'+Math.round(o.rmse_pct_naive)+'% on the whole test set (n='+o.n+'; includes close relatives of training chemicals)</div>';
    h+='<div class="small">RMSE '+sig(o.rmse,3)+' '+esc(epUnits(ep))+'; source: '+esc((sk.source||'').split('/').slice(-2).join('/'))+(sk.variant?'; variant '+esc(sk.variant):'')+'</div>';
  } else h+='<div class="small">No test-error summary found for this model and property.</div>';
  var cv=c.coverage||{};
  h+=(c.interval?'<div class="small" style="margin-top:4px">Range: nominal '+pct(c.interval_level)+'; held for '+(num(cv.empirical_coverage)?pct(cv.empirical_coverage)+' of '+cv.n:'— (not validated)')+' test chemicals in this novelty band; median width '+sig(cv.median_width,3)+'. '+esc(cv.scope||'')+'</div>':'');
  h+='</div>';
  // plain units + spectrum + flags + provenance
  h+='<div><h4>In everyday units</h4>';
  var mw=(rec.input||{}).mw, n=c.interval?natural(ep,c.value,mw):null, nl=n&&natural(ep,c.interval[0],mw), nh=n&&natural(ep,c.interval[1],mw);
  if(n)h+='<div>'+esc(n.t)+' <span class="small">(range '+esc(nl.t)+' to '+esc(nh.t)+')</span></div><div class="small">conversion: '+esc(n.how)+'</div>';
  else h+='<div class="small">Shown in '+esc(epUnits(ep))+'.</div>';
  if((rec.input||{}).has_spectrum){var se=c.spectrum_effect;
    if(se&&se.changed_nothing)h+='<div style="margin-top:6px"><b>The spectrum changed nothing</b> here: '+f(se.value_without_spectrum)+' without vs '+f(c.value)+' with (rule: '+esc(se.rule)+').</div>';
    else if(se&&num(se.delta))h+='<div style="margin-top:6px">Spectrum moved the estimate by '+f(se.delta,3)+' (without it: '+f(se.value_without_spectrum)+').</div>';
    else if((c.flags||[]).some(function(x){return /spectr/.test(x);}))h+='<div style="margin-top:6px"><b>The spectrum was not used</b> by this model, so it changed nothing.</div>';}
  if(c.caveat||c.note_plain)h+='<h4 style="margin-top:8px">Read with care</h4>'+caveatHtml(c,false);
  if(c.familiarity_kind==='spectral_cosine'){h+='<h4 style="margin-top:8px">Spectrum only vs more information</h4><div class="small">Spectrum-only test error '+f((c.skill_naive.overall||{}).rmse_pct_naive,0)+'% of naive'+
    (c.mass_only?'; precursor mass + adduct alone: '+f(c.mass_only.test_pct_naive,0)+'% (estimate '+f(c.mass_only.value)+')':'')+(num(c.structure_same_compounds_pct_naive)?'; with the known structure, same compounds: '+f(c.structure_same_compounds_pct_naive,0)+'%':'')+'.</div>';}
  if(num(c.familiarity_endpoint))h+='<div class="small">Similarity to this property\'s own training chemicals: '+f(c.familiarity_endpoint)+' (the novelty column uses the overall similarity, on which the ranges were checked).</div>';
  var ft=flagText(c.flags);
  if(ft.length)h+='<h4 style="margin-top:8px">Notes</h4><ul class="drv">'+ft.map(function(x){return '<li>'+esc(x)+'</li>';}).join('')+'</ul>';
  h+='<div class="small" style="margin-top:6px">Model: <span class="mono">'+esc(c.model_id)+'</span> ('+esc(c.owner||'')+(c.variant_used?', '+esc(c.variant_used):'')+'), '+esc((c.blocks_used||[]).join('+'))+'</div>';
  if(c.model_id==='W-MODEL_frozen_v5')h+='<div class="small">Model inputs: structure descriptors 2265 + AIMNet2 quantum-chemistry descriptors 31 = 2296 columns, <b>zero spectral features</b> (W-MODEL/frozen_v5/columns.json). A spectrum, if supplied, does not change this estimate.</div>';
  if(c.label_provenance)h+='<div class="small" style="margin-top:6px"><b>Label source:</b> '+esc(c.label_provenance)+'</div>';
  var hz=c.hazard; if(hz){h+='<div class="small">'+esc(hz.band_scheme||'')+'. '+esc(hz.label_caveat||'')+'</div>';}
  return h+'</div></div>';
}

function ghs(mg){return mg<=5?'cat 1':mg<=50?'cat 2':mg<=300?'cat 3':mg<=2000?'cat 4':mg<=5000?'cat 5':'not classified';}
function valueCell(ep,c,rec){
  var mw=(rec.input||{}).mw;
  if(ep==='er_binding'||ep==='ar_agonist'){
    var hz=c.hazard||{}, span=c.interval[0]<0.5&&c.interval[1]>0.5;
    return '<span class="v">'+(span?'inconclusive':esc(hz.band||'?'))+'</span><div class="small">probability active '+f(c.value)+(span?' (most likely: '+esc(hz.band||'?')+')':'')+'</div>'+(span?'<div class="small">the likely range ('+f(c.interval[0])+' to '+f(c.interval[1])+') crosses 0.5, so no call is made</div>':'')+(function(){var br=((DATA.build||{}).base_rates||{})[ep];return br?'<div class="small">base rate: '+(100*br.rate).toFixed(1)+'% of '+br.n+' labelled chemicals are active</div>':'';})();}
  if(c.kind==='classifier'){
    var pr=c.probability<0.001?'<0.001':f(c.probability,3);
    return '<span class="v">'+esc(c.call)+'</span>'+(c.domain==='out'||c.domain==='edge'?' <span class="tag t-edge">▲ low-confidence call</span>':'')+'<div class="small">model probability '+pr+' vs decision threshold '+f(c.threshold,2)+'</div><div class="small">in this novelty band: base rate '+pct(c.base_rate)+' active, PR-AUC '+f(c.pr_auc,2)+' (judge PR-AUC against the base rate; accuracy is not reported)</div>';}
  if(ep==='rat_oral_ld50'&&mw){var mg=Math.pow(10,c.value)*mw, g=ghs(mg), glo=ghs(Math.pow(10,c.interval[0])*mw), ghi=ghs(Math.pow(10,c.interval[1])*mw);
    return '<span class="v">GHS '+g+'</span><div class="small">'+f(c.value)+' '+esc(epUnits(ep))+' ≈ '+sig(mg,2)+' mg/kg</div><div class="small">range covers '+(glo===ghi?'only '+glo:ghi+' → '+glo)+'</div>';}
  if(ep==='rat_oral_LD50'){var hz2=c.hazard||{}, n=natural(ep,c.value,mw);
    return '<span class="v">'+esc(hz2.band||'')+'</span><div class="small">'+f(c.value)+' '+esc(epUnits(ep))+(n?' ≈ '+esc(n.t):'')+'</div>'+(hz2.band_range?'<div class="small">range covers '+esc(hz2.band_range.join(' → '))+'</div>':'');}
  var mo=c.mass_only&&num(c.mass_only.test_pct_naive)?'<div class="small">test error: fragments + mass '+f((c.skill_naive.overall||{}).rmse_pct_naive,0)+'% of naive · mass + adduct alone '+f(c.mass_only.test_pct_naive,0)+'%'+(num(c.structure_same_compounds_pct_naive)?' · known structure '+f(c.structure_same_compounds_pct_naive,0)+'%':'')+'</div>':'';
  if(c.no_skill)return '<span class="v nospin" style="color:#666;font-weight:500">('+f(c.value)+')</span> <b class="small">— no better than guessing the average</b> <span class="u">'+esc(epUnits(ep))+'</span>'+mo;
  if(c.familiarity_kind==='spectral_cosine')return '<span class="v nospin">'+f(c.value)+'</span> <span class="u">'+esc(epUnits(ep))+'</span>'+mo;
  var n2=natural(ep,c.value,mw);
  var nosite=c.caveat&&/no_site/.test(c.caveat.subtype||'');
  if(nosite)return '<span class="v nospin" style="color:#666;font-weight:500">('+f(c.value)+')</span> <span class="u">'+esc(epUnits(ep))+'</span><div class="small">extrapolated value, shown only for reference</div>';
  return '<span class="v nospin">'+f(c.value)+'</span> <span class="u">'+esc(epUnits(ep))+'</span>'+(n2?'<div class="nat">≈ '+esc(n2.t)+'</div>':'');
}

function natRange(ep,c,rec){if(!c.interval)return '';var mw=(rec.input||{}).mw,a=natural(ep,c.interval[0],mw),b=natural(ep,c.interval[1],mw);
  if(!a||!b||ep==='rat_oral_LD50'||/^K/.test(a.t))return '';
  if(ep==='koh_gas')return '<div class="nat">'+esc(b.t.replace('half-life in air ≈ ',''))+' to '+esc(a.t.replace('half-life in air ≈ ',''))+'</div>';
  return '<div class="nat">'+esc(a.t)+' to '+esc(b.t)+'</div>';}
function rowsFor(eps,rec,uid,withEpi){
  var ncol=withEpi?6:5, h='';
  eps.forEach(function(ep,k){
    var c=(rec.endpoints||{})[ep];
    if(!c)return;
    if(c.status==='undefined'){h+=undefRow(ep,c,ncol);return;}
    if(c.status!=='ok'){
      h+='<tr class="main"><td class="prop"><b>'+esc(epLabel(ep))+'</b><span class="hint">'+esc(epWhat(ep))+'</span></td><td colspan="'+(ncol-1)+'"><span class="tag t-na">– '+(c.status==='error'?'model error':'no model for this property in this mode')+'</span>'+
        (c.detail?'<div class="small">'+esc(c.detail)+'</div>':'')+(withEpi?'<div class="small">EPI Suite: '+epiOf(rec,ep,c).html+'</div>':'')+'</td></tr>';return;}
    var e=epiOf(rec,ep,c), tv=truthOf(rec,ep), id=uid+'_'+ep;
    h+='<tr class="main" data-det="'+id+'" tabindex="0" aria-expanded="false"><td class="prop"><b>'+esc(epLabel(ep))+'</b><span class="hint">'+esc(epWhat(ep))+'</span><span class="expand">▸ details</span></td>'+
      '<td>'+valueCell(ep,c,rec)+caveatHtml(c,true)+(num(tv)?'<div class="small">measured: <b>'+f(tv)+'</b> ('+esc((rec.truth[ep]||{}).split||'')+')</div>':'')+'</td>'+
      (c.kind==='classifier'?'<td class="rng small">no interval (classifier)</td>':'<td class="rng"><span class="nospin">'+f(c.interval[0])+' to '+f(c.interval[1])+'</span>'+natRange(ep,c,rec)+rangeBar(ep,c,e.v,tv)+'</td>')+
      '<td>'+(c.kind==='classifier'?'<span class="small">PR-AUC '+f(c.pr_auc,2)+' vs base rate '+pct(c.base_rate)+'</span>':covCell(c))+'</td><td>'+domTag(c.domain,c.familiarity,c.familiarity_kind)+((c.flags||[]).some(function(x){return /OUTSIDE_TRAINING_DESCRIPTOR_RANGE/.test(x);})?'<div class="small"><span class="tag t-edge">▲ extrapolation (size/lipophilicity)</span></div>':'')+(c.domain_reason?'<div class="small"><b>stricter flag:</b> the model\'s own check says '+esc(String(c.domain_flag_model).toLowerCase().replace(/_/g,' '))+'</div>':'')+'</td>'+(withEpi?'<td>'+e.html+(num(e.v)&&(e.v<c.interval[0]||e.v>c.interval[1])?'<div class="small"><span class="tag t-edge">▲ outside our range</span><br>the two methods disagree: treat both with caution</div>':'')+'</td>':'')+'</tr>';
    h+='<tr class="det hid" id="'+id+'"><td colspan="'+ncol+'">'+detailHtml(ep,c,rec)+'</td></tr>';
  });
  return h;
}

function legendHtml(){
  return '<div class="legend"><span>Range bar: <svg width="14" height="12"><rect x="1" y="2" width="12" height="8" fill="#cfe3f1" stroke="#0072B2"/></svg> likely range</span>'+
    '<span><svg width="12" height="14"><path d="M6 1 l5 6 l-5 6 l-5 -6 z" fill="#000"/></svg> estimate</span><span><svg width="12" height="12"><circle cx="6" cy="6" r="4" fill="#fff" stroke="#000" stroke-width="1.5"/></svg> EPI Suite</span>'+
    '<span><svg width="12" height="12"><path d="M2 2 l8 8 m0 -8 l-8 8" stroke="#b34700" stroke-width="2"/></svg> measured (examples only)</span>'+
    '<span>Novelty: <span class="tag t-in">● familiar</span> <span class="tag t-edge">▲ somewhat new</span> <span class="tag t-out">✖ new to the model</span> (less similar training data → expect larger errors)<br><span class="small">Rule: Tanimoto similarity (Morgan radius 2) to the nearest training chemical ≥0.5 = ●, 0.3–0.5 = ▲, &lt;0.3 = ✖; if the model\'s own applicability check is stricter, it wins. The bins and the coverage figures use similarity to the pooled training set of all properties; similarity to the training chemicals of one property can be lower, and the model\'s own check uses the lower of the two (click a row: "Similarity to this property\'s own training chemicals"). It warns of wider ranges and larger errors; it does not mean the range is wrong.</span></span> <a href="#" onclick="setMode(\'about\');document.getElementById(\'glossary\').scrollIntoView();return false;">What do these words mean?</a></div>';
}

var UID=0;
function renderRecord(rec){
  UID++; var u='r'+UID, h=idBox(rec);
  var eps=rec.endpoints||{};
  var fam=FATE.map(function(e){return eps[e];}).filter(function(c){return c&&c.status==='ok'&&num(c.familiarity);}).map(function(c){return c.familiarity;});
  if(fam.length){fam.sort(function(a,b){return a-b;});var md=fam[Math.floor(fam.length/2)];
    var nOut=FATE.filter(function(e){return eps[e]&&eps[e].domain==='out';}).length;
    if(nOut>0)h+='<div class="alert warn"><b>Less similar training data for '+nOut+' of '+FATE.length+' properties (✖ below): expect larger errors.</b>The likely ranges already allow for this: they were calibrated on test chemicals that were just as unfamiliar. Similarity is a weak, graded warning, not a pass/fail test. Median similarity to the nearest training compound: '+f(md)+' (0 = nothing alike, 1 = identical).</div>';}
  var hasFate=FATE.some(function(e){return eps[e];});
  if(hasFate){
    h+='<div class="panel"><h2 style="margin-top:0">Environmental fate</h2>'+legendHtml()+'<div style="overflow-x:auto"><table class="res"><thead><tr><th>Property</th><th>Estimate</th><th>Likely range</th><th>Range held in testing</th><th>New to the model?</th><th>EPI Suite</th></tr></thead><tbody>'+
      rowsFor(FATE,rec,u,true)+'</tbody></table></div><div class="small">Click a row for what drove the estimate, how good the model is, and the value in everyday units. <b>similarity</b> = Tanimoto similarity (0–1) between this structure and the closest chemical the model was trained on; <b>spectral match</b> (spectrum-only mode) = cosine similarity between your spectrum and the closest training spectrum. <b>Range held in testing</b> = how often the measured value of held-out test chemicals, just as new to the model, fell inside their range.</div></div>';}
  var hasHaz=HAZ.some(function(e){return eps[e];});
  if(hasHaz){
    h+='<div class="panel"><h2 style="margin-top:0">Hazard screening <span class="small">(screening-level, not a measurement)</span></h2><div class="small">'+esc((DATA.build||{}).hazard_caveat||'')+'</div><div style="overflow-x:auto"><table class="res"><thead><tr><th>Endpoint</th><th>Call</th><th>Likely range</th><th>Range held in testing</th><th>New to the model?</th></tr></thead><tbody>'+
      rowsFor(HAZ,rec,u,false)+'</tbody></table></div></div>';}
  return h;
}
