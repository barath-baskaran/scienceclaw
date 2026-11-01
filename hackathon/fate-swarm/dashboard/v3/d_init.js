// ===== consistency check (READER-1): Henry implied by VP/WS vs predicted Henry =====
function consistencyHtml(rec){
  var e=rec.endpoints||{},vp=e.vapor_pressure,ws=e.water_solubility,h=e.henry;
  if(!(vp&&ws&&h&&vp.status==='ok'&&ws.status==='ok'&&h.status==='ok'))return '';
  var imp=(vp.value-Math.log10(760))-(ws.value+3)+Math.log10(1)/1;
  // H [atm m3/mol] = (VP/760 atm) / (WS mol/L * 1000 L/m3)
  var d=h.value-imp, bad=Math.abs(d)>1;
  return '<div class="alert '+(bad?'warn':'info')+'"><b>'+(bad?'▲ Consistency check: these three estimates may be inconsistent.':'● Consistency check passed.')+'</b>'+
   'Henry constant implied by the estimated vapour pressure and water solubility: '+f(imp)+' log10 atm·m³/mol; estimated directly: '+f(h.value)+' (difference '+f(d)+' log units'+(bad?', i.e. a factor of '+sig(Math.pow(10,Math.abs(d)),2):'')+'). '+
   'Why it matters: Henry\'s constant should equal vapour pressure divided by solubility. Each property has its own model, so they are not forced to agree; on measured data the relation holds to a median 0.13 log units (READER-1). '+(bad?'At least one of the three is off; use the ranges, not single values.':'')+'</div>';
}
var _renderRecord0=renderRecord;
renderRecord=function(rec){var h=_renderRecord0(rec);var c=consistencyHtml(rec);if(!c)return h;
  var k=h.indexOf('<div class="panel"><h2 style="margin-top:0">Hazard');return k>0?h.slice(0,k)+c+h.slice(k):h+c;};

// ===== "How good is it?" =====
function goodHtml(spectrumFirst){
  var G=DATA.good||{}, h='';
  if(!G.endpoints){return alertBox('warn','No test results embedded.','The build found no evaluation files.');}
  h+='<div class="panel"><h2 style="margin-top:0">How good is it? Test results on chemicals the models never saw</h2>'+
   '<p>Error is shown as a <b>percentage of the error of a naive guess</b> (always predicting the training-set average): 100% = no skill, 50% = half the naive error, lower is better. '+
   '<b>Leak-free first:</b> the first column uses only test chemicals with Tanimoto similarity below 0.40 to every training compound (W-SPACE definition). The remaining columns use the whole test set, which is held out by structural cluster but still contains close relatives of training chemicals, broken down by how new each chemical is (highest Tanimoto similarity to any training compound, <b>nn_sim</b>).</p>'+
   '<p class="small">'+esc(G.note||'')+'</p></div>';
  var bins=G.bins||['<0.3','0.3-0.5','0.5-0.7','>=0.7'];
  var order=spectrumFirst?['spectra','structure']:['structure','spectra'];
  order.forEach(function(sec){
    var S=sec==='structure'?G.endpoints:(G.spectra||{}).endpoints;
    if(sec==='spectra'&&(!S||!Object.keys(S).length)){h+='<div class="panel"><h3>From an MS/MS spectrum only</h3>'+alertBox('warn','▲ No spectrum-only test results yet.',esc((G.spectra||{}).note||''))+'</div>';return;}
    if(!S)return;
    h+='<div class="panel"><h3>'+(sec==='structure'?'From a known structure (this tool) vs EPI Suite':'From an MS/MS spectrum only (no structure)')+'</h3>';
    if(sec==='spectra')h+='<p class="small">'+esc((G.spectra||{}).note||'')+'</p>';
    h+='<div style="overflow-x:auto"><table class="sk"><thead><tr><th>Property</th><th>method</th><th>leak-free<br>(Tanimoto&lt;0.40)</th><th>all test</th>'+bins.map(function(b){return '<th>nn_sim '+esc(b)+'</th>';}).join('')+'<th>range held<br>(nominal)</th></tr></thead><tbody>';
    Object.keys(S).forEach(function(ep){var rows=S[ep].rows||[];
      rows.forEach(function(r,i){
        h+='<tr><td>'+(i===0?'<b>'+esc(epLabel(ep))+'</b>':'')+'</td><td>'+esc(r.method)+'</td><td>'+cellPct(r.leak_free)+'</td><td>'+cellPct(r.overall)+'</td>'+bins.map(function(b){return '<td>'+cellPct((r.bins||{})[b])+'</td>';}).join('')+
          '<td>'+(r.coverage&&num(r.coverage.empirical)?pct(r.coverage.empirical)+' <span class="small">held'+(r.coverage.n?' (n='+r.coverage.n+')':'')+' at nominal '+pct(r.coverage.nominal)+'</span>'+((r.coverage.leak_free&&num(r.coverage.leak_free.empirical))?'<br><span class="small">leak-free: '+pct(r.coverage.leak_free.empirical)+' held (n='+r.coverage.leak_free.n+')</span>':'')+'<br><span class="small">by similarity: '+Object.keys(r.coverage.bins||{}).filter(function(b){return r.coverage.bins[b];}).map(function(b){return esc(b)+' '+pct(r.coverage.bins[b].empirical)+' (n='+r.coverage.bins[b].n+')';}).join(', ')+'</span>':'<span class="small">no interval</span>')+'</td></tr>';});
      if(S[ep].note)h+='<tr><td></td><td colspan="'+(bins.length+4)+'" class="small">'+esc(S[ep].note)+'</td></tr>';});
    h+='</tbody></table></div><div class="small">Cell = error as % of naive (n test chemicals), lower is better; 95% CI = cluster bootstrap; ▼ better / ▲ worse / ≈ not resolved vs EPI Suite on the same chemicals (paired 95% CI of the difference excludes 0 or not). Bars: ▇ length = % of naive, capped at 150%. Sources: '+esc(((sec==='structure'?G.sources:(G.spectra||{}).sources)||[]).join('; '))+'</div></div>';
  });
  if(G.undefined_cells&&G.undefined_cells.length){
    h+='<div class="panel"><h3>Where a property is not defined vs where data are simply missing (W-SPACE)</h3><div style="overflow-x:auto"><table class="sk"><thead><tr>'+Object.keys(G.undefined_cells[0]).map(function(k){return '<th>'+esc(k)+'</th>';}).join('')+'</tr></thead><tbody>'+
      G.undefined_cells.map(function(r){return '<tr>'+Object.keys(r).map(function(k){return '<td>'+esc(r[k])+'</td>';}).join('')+'</tr>';}).join('')+'</tbody></table></div></div>';}
  return h;
}
function cellPct(m){if(m&&m.too_few)return '<span class="small">n='+m.n+', too few</span>';if(!m||!num(m.pct))return '<span class="small">–</span>';var w=Math.min(150,m.pct)/150*60;
  var ci=(m.ci95&&num(m.ci95[0]))?'<br><span class="small">95% CI '+Math.round(m.ci95[0])+'–'+Math.round(m.ci95[1])+'%'+(m.ci95[1]>=100?' ▲ crosses 100%: skill not established':'')+'</span>':'';
  var ve=m.vs_epi?'<br><span class="small">'+(m.vs_epi.indexOf('better')===0?'▼ ':m.vs_epi.indexOf('worse')===0?'▲ ':'≈ ')+esc(m.vs_epi)+'</span>':'';
  return '<span class="nospin">'+Math.round(m.pct)+'%</span> <span class="small">('+m.n+')</span>'+ci+ve+'<br><svg width="62" height="6"><rect width="'+w.toFixed(1)+'" height="6" fill="'+(m.pct>=100?'#b34700':'#0072B2')+'"/>'+(m.pct>=100?'':'')+'<line x1="40" y1="0" x2="40" y2="6" stroke="#000"/></svg>';}

function aboutHtml(){
  var B=DATA.build||{}, h='<div class="panel"><h2 style="margin-top:0">What is behind it</h2><ul>'+(B.about||[]).map(function(x){return '<li>'+esc(x)+'</li>';}).join('')+'</ul></div>';
  h+='<div class="panel"><h3>Models used (frozen)</h3><table class="sk"><thead><tr><th>model</th><th>owner</th><th>inputs</th><th>properties</th></tr></thead><tbody>'+(DATA.models||[]).map(function(m){
    return '<tr><td class="mono">'+esc(m.model_id)+'</td><td>'+esc(m.owner)+'</td><td>'+esc((m.feature_blocks||[]).join(', '))+'</td><td style="text-align:left">'+esc((m.endpoints||[]).join(', '))+'</td></tr>';}).join('')+'</tbody></table></div>';
  h+='<div class="panel"><h3>Properties and units</h3><table class="sk"><thead><tr><th>property</th><th>units</th><th>meaning</th><th>EPI Suite module</th></tr></thead><tbody>'+Object.keys(EPM).map(function(ep){var e=EPM[ep];
    return '<tr><td>'+esc(e.label)+'</td><td>'+esc(e.units)+'</td><td style="text-align:left">'+esc(e.what)+'</td><td>'+esc(e.epi||'none')+'</td></tr>';}).join('')+'</tbody></table></div>';
  h+='<div class="panel" id="glossary"><h3>Glossary</h3><dl class="kv">'+[
   ['log10 units','Many properties span orders of magnitude, so they are given as the base-10 logarithm: 2 means 100, -3 means 0.001. A difference of 1 is a factor of 10.'],
   ['Kow, Koa, Koc, BCF','Partition/sorption constants: octanol–water (fat vs water), octanol–air, soil organic carbon–water, and fish–water (bioconcentration factor).'],
   ['pKa','The pH at which an acidic or basic group is half ionised.'],
   ['Likely range (conformal)','A range built so that, on held-out test chemicals, it contained the measured value about 90% of the time. We show how often it actually did, for chemicals as new as yours.'],
   ['Similarity (Tanimoto)','0–1 overlap of substructures between your structure and the closest training chemical. Low similarity means larger expected errors.'],
   ['Spectral match','Cosine similarity (0–1) between your MS/MS spectrum and the closest training spectrum.'],
   ['Naive guess','Always predicting the training-set average. Error as % of naive: 100% = no skill, lower is better.'],
   ['Leak-free','Test chemicals with Tanimoto below 0.40 to every training chemical: the honest test for new chemistry.'],
   ['SHAP','A standard way to split a model prediction into contributions of its inputs; ▲ raises / ▼ lowers the estimate by the stated amount.'],
   ['Quantum chemistry (AIMNet2)','A neural-network quantum-chemistry model; we relax a 3D structure and use charges, dipole, surface areas as extra inputs.'],
   ['EPI Suite modules','US EPA\'s standard estimation programs: KOWWIN (Kow), WSKOWWIN (solubility), MPBPVP (melting/boiling point, vapour pressure), HENRYWIN, KOCWIN, BCFBAF, KOAWIN, AOPWIN (OH rate).'],
   ['OPERA','A set of EPA QSAR models; ER/AR labels here are OPERA consensus calls (model outputs, not measurements).'],
   ['GHS category','Globally Harmonized System acute oral toxicity bands: cat 1 (LD50 ≤ 5 mg/kg, most toxic) to cat 5 (2000–5000 mg/kg).'],
   ['Not physically defined','The quantity does not exist for this kind of species (e.g. vapour pressure of a permanent ion). Different from missing data.']].map(function(g){return '<dt><b>'+esc(g[0])+'</b></dt><dd>'+esc(g[1])+'</dd>';}).join('')+'</dl></div>';
  h+='<div class="panel small">Built '+esc(B.built_utc||'')+'. '+esc(B.files_note||'')+'</div>';
  return h;
}

// ===== batch =====
function batchTable(rows){
  BATCH=rows;var eps=FATE.concat(HAZ);
  var h='<table class="sk"><thead><tr><th>SMILES</th>'+eps.map(function(e){return '<th>'+esc(epLabel(e))+'</th>';}).join('')+'</tr></thead><tbody>';
  rows.forEach(function(r){h+='<tr><td class="mono" style="text-align:left">'+esc(r.smiles)+'</td>';
    eps.forEach(function(e){var c=r.rec&&r.rec.endpoints[e];
      if(!r.rec){h+='<td class="small">not computed</td>';return;}
      if(!c||c.status==='undefined'){h+='<td class="small">'+(c?'⊘ undefined':'–')+'</td>';return;}
      if(c.status!=='ok'){h+='<td class="small">–</td>';return;}
      var sym={'in':'●','edge':'▲','out':'✖'}[c.domain]||'?';
      h+='<td>'+f(c.value)+' <span class="small">['+f(c.interval[0])+', '+f(c.interval[1])+'] '+sym+'</span></td>';});
    h+='</tr>';});
  $('b_table').innerHTML=h+'</tbody></table><div class="small">● familiar ▲ somewhat new ✖ new to the model; ⊘ not defined for this compound. Ranges are the nominal 90% intervals; see the structure view for their tested coverage.</div>';
}
function batchCsv(){
  if(!BATCH.length)return;var out=['smiles,endpoint,status,value,units,lo,hi,interval_nominal,empirical_coverage_bin,n_bin,familiarity,domain,epi_value,model_id,reason'];
  BATCH.forEach(function(r){if(!r.rec){out.push('"'+r.smiles+'",,not_computed,,,,,,,,,,,,');return;}
    Object.keys(r.rec.endpoints).forEach(function(e){var c=r.rec.endpoints[e],cv=c.coverage||{};
      out.push(['"'+r.smiles+'"',e,c.status,c.value,'"'+epUnits(e)+'"',c.interval?c.interval[0]:'',c.interval?c.interval[1]:'',c.interval_level,cv.empirical_coverage,cv.n,c.familiarity,c.domain,(c.epi||{}).value,c.model_id,'"'+String(c.reason||'').replace(/"/g,"'")+'"'].map(function(x){return x==null?'':x;}).join(','));});});
  var a=document.createElement('a');a.href=URL.createObjectURL(new Blob([out.join('\n')],{type:'text/csv'}));a.download='fate_predictions.csv';a.click();
}

// ===== init =====
function init(){
  $('m-struct').onclick=function(){setMode('struct');};$('m-spec').onclick=function(){setMode('spec');};
  $('m-batch').onclick=function(){setMode('batch');};$('m-good').onclick=function(){setMode('good');};$('m-about').onclick=function(){setMode('about');};
  $('specform1').innerHTML=specForm('a_');$('specform2').innerHTML=specForm('u_');
  ['a_','u_'].forEach(function(p){$(p+'peaks').oninput=function(){var s=readSpec(p,false).spectrum;$(p+'plot').innerHTML=s?specPlot(s):'';};});
  var ex=DATA.examples||[];
  $('exchips').innerHTML='<span class="small" style="align-self:center">Examples:</span>'+ex.map(function(e,i){return '<button class="chip" data-i="'+i+'" title="'+esc(e.rec.input.smiles)+'">'+esc(e.short)+'</button>';}).join('');
  Array.prototype.forEach.call(document.querySelectorAll('#exchips .chip'),function(b){b.onclick=function(){var e=ex[+b.getAttribute('data-i')];$('smi').value=e.rec.input.smiles;
     if(LIVE){predictStruct();}else{show('out',e.rec);$('msg').innerHTML=alertBox('info','Precomputed example: '+esc(e.short)+'.',esc(e.why||'')+' Computed when the page was built ('+esc((DATA.build||{}).built_utc||'')+').');}};});
  var sx=DATA.spec_examples||[];
  $('specchips').innerHTML=sx.length?'<span class="small" style="align-self:center">Example spectra:</span>'+sx.map(function(e,i){return '<button class="chip" data-i="'+i+'">'+esc(e.short)+'</button>';}).join(''):'';
  Array.prototype.forEach.call(document.querySelectorAll('#specchips .chip'),function(b){b.onclick=function(){var e=sx[+b.getAttribute('data-i')];fillSpec('u_',e.rec.input.spectrum);
     if(LIVE)predictSpec();else{show('u_out',e.rec);$('u_msg').innerHTML=alertBox('info','Precomputed example.',esc(e.why||''));}};});
  $('go').onclick=predictStruct;$('smi').onkeydown=function(ev){if(ev.key==='Enter')predictStruct();};
  $('u_go').onclick=predictSpec;
  $('loadbtn').onclick=function(){$('loadfile').click();};
  $('loadfile').onchange=function(){var fl=this.files[0];if(!fl)return;var rd=new FileReader();rd.onload=function(){try{var j=JSON.parse(rd.result);var R=j.records||[j];
      if(R.length===1)show('out',R[0]);else{setMode('batch');batchTable(R.map(function(r){return {smiles:(r.input||{}).smiles,rec:r};}));}
      $('msg').innerHTML=alertBox('info','Opened '+esc(fl.name)+'.',R.length+' record(s), created '+esc(j.created_utc||'?')+'.');}catch(e){$('msg').innerHTML=alertBox('err','Could not read that file.',esc(String(e)));}};rd.readAsText(fl);};
  $('b_go').onclick=function(){var L=$('b_text').value.split(/\n/).map(function(x){return x.trim().split(/[\s,]+/)[0];}).filter(Boolean);
    if(!L.length){$('b_msg').innerHTML=alertBox('err','Nothing to run.','Paste SMILES, one per line, or choose a file.');return;}
    if(LIVE)return runLive({smiles_list:L,physics:false},$('b_log'),function(res,err){if(!res){$('b_msg').innerHTML=alertBox('err','Batch failed.',esc(err||''));return;}batchTable(L.map(function(s,i){return {smiles:s,rec:res.records[i]};}));});
    var rows=L.map(function(s){return {smiles:s,rec:findExample(s)};});batchTable(rows);var n=rows.filter(function(r){return !r.rec;}).length;
    $('b_msg').innerHTML=n?offlineMsg('batch ('+n+' of '+rows.length+' structures are not precomputed)'):'';};
  $('b_file').onchange=function(){var fl=this.files[0];if(!fl)return;var rd=new FileReader();rd.onload=function(){var L=rd.result.split(/\n/);var hdr=L[0].split(/[,\t]/).map(function(x){return x.trim().toLowerCase();});var ci=hdr.indexOf('smiles');
      $('b_text').value=(ci>=0?L.slice(1).map(function(l){return (l.split(/[,\t]/)[ci]||'').trim();}):L.map(function(l){return l.trim().split(/\s+/)[0];})).filter(Boolean).join('\n');};rd.readAsText(fl);};
  $('b_csv').onclick=batchCsv;
  $('good').innerHTML=goodHtml(false);$('u_good').innerHTML=goodHtml(true);$('about').innerHTML=aboutHtml();
  $('physnote').textContent=(DATA.build||{}).physics_note||'';
  $('foot').innerHTML='Built '+esc((DATA.build||{}).built_utc||'')+' · predictions come only from the swarm\'s frozen models · works offline · '+esc((DATA.build||{}).version||'');
  var setLive=function(on){LIVE=on;$('modeline').innerHTML=on?alertBox('info','● Connected to the local tool.','New structures and spectra are computed on this computer now.'):
     alertBox('warn','▲ Viewing mode (opened as a file).','You can browse the precomputed examples, test results and an opened results file. To estimate a NEW structure or spectrum start the local tool: <span class="mono">'+esc((DATA.build||{}).start_cmd||'')+'</span>');
     $('usephys').disabled=!on;};
  setLive(false);
  if(/^http/.test(location.protocol)&&window.fetch){fetch('/api/models').then(function(r){return r.ok?r.json():null;}).then(function(j){if(j)setLive(true);}).catch(function(){});}
}
if(typeof document!=='undefined'&&document.getElementById('go'))init();
