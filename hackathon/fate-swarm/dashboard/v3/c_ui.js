// ===== UI wiring =====
var LIVE=false, BATCH=[];
var MODES=['struct','spec','batch','good','about'];
function setMode(m){
  MODES.forEach(function(x){var s=$('s-'+x);if(s)s.classList.toggle('hid',x!==m);});
  $('m-struct').classList.toggle('on',m==='struct');$('m-spec').classList.toggle('on',m==='spec');
  $('m-struct').setAttribute('aria-selected',m==='struct');$('m-spec').setAttribute('aria-selected',m==='spec');
  ['batch','good','about'].forEach(function(x){$('m-'+x).classList.toggle('on',m===x);});
}
function bindRows(root){
  Array.prototype.forEach.call(root.querySelectorAll('tr.main[data-det]'),function(tr){
    var tog=function(){var d=$(tr.getAttribute('data-det'));if(!d)return;var open=d.classList.contains('hid');d.classList.toggle('hid',!open);tr.setAttribute('aria-expanded',open);
      var ex=tr.querySelector('.expand');if(ex)ex.textContent=open?'▾ hide details':'▸ details';};
    tr.onclick=tog;tr.onkeydown=function(ev){if(ev.key==='Enter'||ev.key===' '){ev.preventDefault();tog();}};});
}
function show(target,rec){$(target).innerHTML=renderRecord(rec);bindRows($(target));}
function alertBox(kind,title,body){return '<div class="alert '+kind+'"><b>'+title+'</b>'+body+'</div>';}

// ---- spectrum form (shared by both modes) — required metadata is checked, never defaulted
var ADDUCTS=['[M+H]+','[M+Na]+','[M+NH4]+','[M]+','[M-H]-','[M+Cl]-','[M+FA-H]-','[M+HCOO]-'];
function specForm(p){
  return '<div class="row"><div><label for="'+p+'ion">Ionisation *</label><select id="'+p+'ion"><option value="">choose…</option><option value="ESI">ESI (LC-MS/MS)</option><option value="EI">EI (GC-MS)</option></select></div><div><label for="'+p+'pol">Ion mode *</label><select id="'+p+'pol"><option value="">choose…</option><option>positive</option><option>negative</option></select></div>'+
   '<div><label for="'+p+'add">Adduct / ion type *</label><select id="'+p+'add"><option value="">choose…</option>'+ADDUCTS.map(function(a){return '<option>'+a+'</option>';}).join('')+'</select></div>'+
   '<div><label for="'+p+'prec">Precursor m/z *</label><input id="'+p+'prec" type="number" step="any" placeholder="e.g. 195.0877"></div>'+
   '<div><label for="'+p+'ce">Collision energy (eV) *</label><input id="'+p+'ce" type="number" step="any" placeholder="e.g. 20"><label class="check" style="margin-top:4px"><input type="checkbox" id="'+p+'ceu"> unknown</label></div>'+
   '<div><label for="'+p+'ins">Instrument *</label><select id="'+p+'ins"><option value="">choose…</option><option value="orbitrap">Orbitrap</option><option value="tof">Q-TOF</option><option value="qqq">triple quad</option><option value="ion_trap">ion trap</option><option value="unknown">unknown</option></select></div></div>'+
   '<label for="'+p+'peaks">Fragment peaks * <span class="hint">one per line: m/z then intensity (space, tab, comma or colon between)</span></label><textarea id="'+p+'peaks" placeholder="91.0542 100&#10;119.0491 35.2"></textarea>'+
   '<div id="'+p+'plot"></div>';
}
function parsePeaks(txt){
  var mz=[],it=[],bad=[];
  String(txt||'').split(/\n/).forEach(function(l,i){l=l.trim();if(!l||l[0]==='#')return;var p=l.split(/[\s,;:]+/).map(Number);
    if(p.length>=2&&isFinite(p[0])&&isFinite(p[1])&&p[0]>0&&p[1]>=0){mz.push(p[0]);it.push(p[1]);}else bad.push(i+1);});
  return {mz:mz,intensity:it,bad:bad};
}
function readSpec(p,required){
  var pol=$(p+'pol').value, add=$(p+'add').value, prec=parseFloat($(p+'prec').value), ceu=$(p+'ceu').checked, ce=parseFloat($(p+'ce').value), ins=$(p+'ins').value;
  var pk=parsePeaks($(p+'peaks').value), miss=[], ion=$(p+'ion').value;
  var any=ion||pol||add||isFinite(prec)||pk.mz.length||isFinite(ce)||ins;
  if(!any&&!required)return {spectrum:null};
  if(!ion)miss.push('ionisation (ESI or EI)');
  if(ion!=='EI'){if(!pol)miss.push('ion mode');if(!add)miss.push('adduct / ion type');if(!isFinite(prec))miss.push('precursor m/z');}
  if(ion!=='EI'&&!ceu&&!isFinite(ce))miss.push('collision energy (or tick "unknown")');if(!ins)miss.push('instrument (choose "unknown" if you do not know)');
  if(pk.mz.length<1)miss.push('at least one fragment peak');
  if(ion!=='EI'&&pol&&add&&((pol==='positive')!==/\]\+$/.test(add)))miss.push('ion mode and adduct disagree ('+pol+' vs '+add+')');
  var err=miss.length?'Missing or inconsistent: '+miss.join('; ')+'.':null;
  if(pk.bad.length)err=(err?err+' ':'')+'Could not read peak line(s) '+pk.bad.slice(0,8).join(', ')+'.';
  return {err:err,spectrum:{mz:pk.mz,intensity:pk.intensity,meta:{ionisation:ion,polarity:pol,ionization_mode:pol,adduct:add,precursor_mz:prec,collision_energy_eV:ceu?null:ce,collision_energy:ceu?null:ce,ce_unknown:ceu,instrument_class:ins}}};
}
function specPlot(s){
  if(!s||!s.mz||!s.mz.length)return '';
  var W=560,H=140,P=30,mx=Math.max.apply(null,s.mz.concat([(s.meta||{}).precursor_mz||0]))*1.05,mi=Math.max.apply(null,s.intensity)||1;
  var g='<svg class="specplot" width="100%" viewBox="0 0 '+W+' '+H+'" role="img" aria-label="spectrum stick plot"><line x1="'+P+'" y1="'+(H-20)+'" x2="'+(W-5)+'" y2="'+(H-20)+'" stroke="#444"/>';
  s.mz.forEach(function(m,i){var x=P+(W-P-5)*m/mx, y=(H-20)-(H-30)*s.intensity[i]/mi;g+='<line x1="'+x.toFixed(1)+'" y1="'+(H-20)+'" x2="'+x.toFixed(1)+'" y2="'+y.toFixed(1)+'" stroke="#000" stroke-width="1.5"><title>'+m+' : '+s.intensity[i]+'</title></line>';});
  var pm=(s.meta||{}).precursor_mz;if(num(pm)){var xp=P+(W-P-5)*pm/mx;g+='<path d="M'+xp.toFixed(1)+' '+(H-18)+' l-5 10 h10 z" fill="#E69F00" stroke="#000"><title>precursor '+pm+'</title></path>';}
  for(var t=0;t<=4;t++){var mzv=mx*t/4;g+='<text x="'+(P+(W-P-5)*t/4).toFixed(0)+'" y="'+(H-2)+'" font-size="10" text-anchor="middle">'+mzv.toFixed(0)+'</text>';}
  return g+'<text x="'+(W-5)+'" y="12" font-size="10" text-anchor="end">m/z (▲ = precursor)</text></svg>';
}

// ---- live backend (only when served by tool/serve.py on 127.0.0.1) ----
function runLive(body,logEl,done){
  logEl.classList.remove('hid');logEl.textContent='submitting…';
  fetch('/api/predict',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(body)}).then(function(r){return r.json();}).then(function(j){
    if(!j.job){logEl.textContent='error: '+(j.error||'no job');done(null,j.error||'server refused');return;}
    var poll=function(){fetch('/api/job/'+j.job).then(function(r){return r.json();}).then(function(s){
      logEl.textContent=(s.log||[]).map(function(x){return '['+f(x.t,1)+' s] '+x.msg;}).join('\n')+'\n… '+s.status+' — '+f(s.elapsed_s,0)+' s elapsed';
      logEl.scrollTop=1e9;
      if(s.status==='done')done(s.result);else if(s.status==='error')done(null,(s.log||[]).slice(-1).map(function(x){return x.msg;})[0]);else setTimeout(poll,800);});};
    poll();}).catch(function(e){done(null,'cannot reach the local tool server: '+e);});
}
function offlineMsg(what){
  return alertBox('err','This copy of the page cannot compute a new '+what+'.',
   'It is a viewer: it contains only the precomputed examples (the buttons above) and any results file you open. New structures need the companion program, which is started with one command (see README.md next to this file) — or ask whoever sent you this file to run your structure and send you the results file. '+
   '<details style="margin-top:6px"><summary>For the person running the program</summary><div class="mono" style="margin:6px 0">'+esc((DATA.build||{}).start_cmd||'bash start_dashboard.sh')+'</div>then open <span class="mono">http://127.0.0.1:8765</span>. It runs on this computer only; the EPI Suite comparison needs internet and is skipped without it.</details>');
}
function findExample(s){
  s=(s||'').trim();var ex=DATA.examples||[];
  for(var i=0;i<ex.length;i++){var r=ex[i].rec,inp=r.input||{};if(inp.smiles===s||inp.canonical_smiles===s)return r;}
  return null;
}
function predictStruct(){
  var smi=$('smi').value.trim();$('msg').innerHTML='';
  if(!smi){$('msg').innerHTML=alertBox('err','Please enter a structure.','Paste a SMILES string in the box, or click one of the examples.');$('smi').focus();return;}
  if(/\s/.test(smi)){$('msg').innerHTML=alertBox('err','The SMILES contains a space.','A SMILES string has no spaces. If you pasted a name, convert it to SMILES first (this tool does not look names up).');return;}
  var sp=readSpec('a_',false);
  if(sp.err){$('msg').innerHTML=alertBox('err','The optional spectrum is incomplete.',esc(sp.err)+' Fill it in or clear it; nothing is filled in for you.');return;}
  if(!LIVE){var r=findExample(smi);
    if(r&&!sp.spectrum){show('out',r);$('msg').innerHTML=alertBox('info','Precomputed example.','This structure was run through the models when the page was built ('+esc((DATA.build||{}).built_utc||'')+').');return;}
    $('msg').innerHTML=offlineMsg('structure');$('out').innerHTML='';return;}
  $('go').disabled=true;$('out').innerHTML='';
  runLive({smiles:smi,physics:$('usephys').checked,spectrum:sp.spectrum},$('runlog'),function(res,err){$('go').disabled=false;
    if(!res){$('msg').innerHTML=alertBox('err','The prediction failed.',esc(err||''));return;}
    var r=res.records[0];
    if((r.errors||[]).length&&!Object.keys(r.endpoints||{}).length){$('msg').innerHTML=alertBox('err','The structure could not be read.',r.errors.map(esc).join('<br>')+'<br>Check the SMILES (brackets, ring-closure digits, charges).');return;}
    show('out',r);});
}
function predictSpec(){
  $('u_msg').innerHTML='';var sp=readSpec('u_',true);
  if(sp.err){$('u_msg').innerHTML=alertBox('err','Cannot estimate yet.',esc(sp.err)+' The spectrum-only model needs all starred fields; it never guesses missing metadata.');return;}
  if(!LIVE){$('u_msg').innerHTML=offlineMsg('spectrum');return;}
  $('u_go').disabled=true;
  runLive({spectrum:sp.spectrum},$('u_log'),function(res,err){$('u_go').disabled=false;if(!res){$('u_msg').innerHTML=alertBox('err','The prediction failed.',esc(err||''));return;}show('u_out',res.records[0]);});
}
function fillSpec(p,s){var m=s.meta||{};$(p+'ion').value=m.ionisation||'';$(p+'pol').value=m.polarity||m.ionization_mode||'';$(p+'add').value=m.adduct||'';$(p+'prec').value=m.precursor_mz||'';
  $(p+'ce').value=num(m.collision_energy_eV)?m.collision_energy_eV:'';$(p+'ceu').checked=!num(m.collision_energy_eV);
  $(p+'ins').value=({qtof:'tof','q-tof':'tof'})[m.instrument_class]||m.instrument_class||'unknown';
  $(p+'peaks').value=s.mz.map(function(x,i){return x+' '+s.intensity[i];}).join('\n');$(p+'plot').innerHTML=specPlot(s);}
