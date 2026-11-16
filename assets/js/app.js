(() => {
  const state = { catalog: null, lang: "zh-CN", view: "all", query: "", category: null, detail: null, detailLang: "zh-CN" };
  const $ = (selector, root=document) => root.querySelector(selector);
  const $$ = (selector, root=document) => [...root.querySelectorAll(selector)];
  const i18n = {
    "zh-CN": {eyebrow:"CURATED AI WORKFLOWS",heroTitle:"找到适合你的 AI 工作流",heroDescription:"浏览插件与 Skill，按能力、角色和任务场景发现可复用的工作方式。",searchPlaceholder:"搜索 Plugin、Skill 或关键词",browseBy:"按维度浏览",dataNoteTitle:"数据说明",dataNote:"分类仅展示已审核关联；尚未审核的候选不会作为正式分类结果。",allResources:"全部资源",allResourcesDesc:"浏览当前收录的 Plugin 与 Skill。",all:"全部",emptyTitle:"没有找到匹配的资源",emptyDescription:"试试其他关键词，或清除当前筛选条件。",clearFilters:"清除筛选",poweredBy:"数据来源",plugins:"插件",skills:"Skill",functions:"功能",roles:"角色",scenarios:"场景",tags:"标签",pluginCount:"Plugins",skillCount:"Skills",translationCount:"已审核中文译文",showing:"显示",results:"项资源",noCategories:"暂无已审核分类关联",viewSkill:"查看 Skill",viewPlugin:"查看 Plugin",back:"返回资源列表",source:"上游原文",translation:"中文译文",english:"English 原文",translationNote:"此译文已审核，仅用于阅读；安装和执行请以英文上游原文为准。",noTranslation:"该 Skill 暂无已审核的中文译文。",skillsInPlugin:"此 Plugin 收录的 Skills",noSkills:"当前没有可展示的 Skill。",openSource:"查看上游",unclassified:"尚无已审核分类",allCategories:"全部资源",searchResults:"搜索结果"},
    "en": {eyebrow:"CURATED AI WORKFLOWS",heroTitle:"Discover AI workflows that fit your work",heroDescription:"Explore plugins and Skills by capability, role, and task scenario.",searchPlaceholder:"Search plugins, Skills, or keywords",browseBy:"Browse by taxonomy",dataNoteTitle:"About the data",dataNote:"Only reviewed assignments appear as official categories. Pending proposals are excluded.",allResources:"All resources",allResourcesDesc:"Browse the Plugins and Skills currently indexed.",all:"All",emptyTitle:"No matching resources",emptyDescription:"Try another keyword or clear the active filters.",clearFilters:"Clear filters",poweredBy:"Source",plugins:"Plugins",skills:"Skills",functions:"Functions",roles:"Roles",scenarios:"Scenarios",tags:"Tags",pluginCount:"Plugins",skillCount:"Skills",translationCount:"Reviewed Chinese translations",showing:"Showing",results:"resources",noCategories:"No reviewed category assignments yet",viewSkill:"View Skill",viewPlugin:"View Plugin",back:"Back to resources",source:"Upstream source",translation:"Chinese translation",english:"English source",translationNote:"Reviewed translation for reading only. Use the upstream English source for installation and execution.",noTranslation:"No reviewed Chinese translation is available for this Skill.",skillsInPlugin:"Skills in this Plugin",noSkills:"No Skills are available for this Plugin.",openSource:"Open upstream",unclassified:"No reviewed categories",allCategories:"All resources",searchResults:"Search results"}
  };
  const t = key => i18n[state.lang][key] || key;
  const escapeHtml = value => String(value ?? "").replace(/[&<>"']/g, ch => ({"&":"&amp;","<":"&lt;",">":"&gt;",'"':"&quot;","'":"&#39;"}[ch]));
  const nameOf = item => item?.name?.[state.lang] || item?.name?.["zh-CN"] || item?.name?.en || item?.display_name || item?.name || item?.id || "";
  const pluginName = plugin => plugin.display_name || plugin.name || plugin.id;
  const categoryMap = () => new Map(Object.values(state.catalog.taxonomy).flat().map(item => [item.id,item]));
  const approvedNames = skill => Object.values(skill.approved_categories || {}).flat().map(item => categoryMap().get(item.category_id)).filter(Boolean).map(nameOf);
  const markdownInline = text => {
    let value = escapeHtml(text);
    value = value.replace(/\[([^\]]+)\]\((https?:\/\/[^\s)]+)\)/g, '<a href="$2" target="_blank" rel="noreferrer">$1</a>');
    value = value.replace(/\*\*([^*]+)\*\*/g, "<strong>$1</strong>").replace(/\*([^*]+)\*/g,"<em>$1</em>").replace(/`([^`]+)`/g,"<code>$1</code>");
    return value;
  };
  function renderMarkdown(source) {
    const lines = String(source || "").replace(/\r\n/g,"\n").split("\n");
    const out=[]; let paragraph=[]; let list=null; let code=null;
    const flushParagraph=()=>{if(paragraph.length){out.push("<p>"+paragraph.map(markdownInline).join("<br>")+"</p>");paragraph=[];}};
    const flushList=()=>{if(list){out.push("</"+list+">");list=null;}};
    for(const line of lines){
      if(code!==null){if(/^\s*```/.test(line)){out.push("</code></pre>");code=null;}else out.push(escapeHtml(line));continue;}
      const fence=line.match(/^\s*```/);
      if(fence){flushParagraph();flushList();code=true;out.push("<pre><code>");continue;}
      if(!line.trim()){flushParagraph();flushList();continue;}
      const heading=line.match(/^(#{1,6})\s+(.+)$/);
      if(heading){flushParagraph();flushList();const level=heading[1].length;out.push("<h"+level+">"+markdownInline(heading[2])+"</h"+level+">");continue;}
      if(/^\s*---+\s*$/.test(line)){flushParagraph();flushList();out.push("<hr>");continue;}
      if(/^>\s?/.test(line)){flushParagraph();flushList();out.push("<blockquote>"+markdownInline(line.replace(/^>\s?/,""))+"</blockquote>");continue;}
      const unordered=line.match(/^\s*[-*+]\s+(.+)$/), ordered=line.match(/^\s*\d+[.)]\s+(.+)$/);
      if(unordered||ordered){flushParagraph();const kind=unordered?"ul":"ol";if(list!==kind){flushList();list=kind;out.push("<"+list+">");}out.push("<li>"+markdownInline((unordered||ordered)[1])+"</li>");continue;}
      flushList();paragraph.push(line);
    }
    flushParagraph();flushList();if(code!==null)out.push("</code></pre>");
    return out.join("\n");
  }
  function renderStats(){
    const c=state.catalog.counts;
    $("#stats").innerHTML=[
      [c.plugins,t("pluginCount"),"◈"],[c.skills,t("skillCount"),"⌘"],[c.reviewed_translations,t("translationCount"),"文"]
    ].map(([n,label,icon])=>'<div class="stat-card"><div><div class="stat-label">'+escapeHtml(label)+'</div><div class="stat-value">'+Number(n).toLocaleString()+'</div></div><div class="stat-icon">'+icon+'</div></div>').join("");
    $("#hero-meta").textContent=t("showing")+" "+c.plugins+" "+t("plugins")+" · "+c.skills+" "+t("skills");
  }
  function renderTaxonomy(){
    const labels={functions:t("functions"),roles:t("roles"),scenarios:t("scenarios"),tags:t("tags")};
    const map=categoryMap();const counts={};
    for(const dimension of Object.keys(state.catalog.taxonomy)){
      for(const node of state.catalog.taxonomy[dimension]) counts[node.id]=state.catalog.aggregation.dimensions?.[dimension]?.[node.id]?.skill_ids?.length||0;
    }
    $("#taxonomy-nav").innerHTML=Object.entries(state.catalog.taxonomy).map(([dimension,nodes])=>{
      const active=nodes.filter(n=>n.status==="active").sort((a,b)=>(a.sort_order||0)-(b.sort_order||0));
      if(!active.length)return "";
      return '<div class="taxonomy-group"><div class="taxonomy-title">'+escapeHtml(labels[dimension])+'</div>'+active.map(node=>'<button type="button" class="taxonomy-link '+(state.category===node.id?"active":"")+'" data-category="'+escapeHtml(node.id)+'"><span>'+escapeHtml(nameOf(node))+'</span><span class="taxonomy-count">'+counts[node.id]+'</span></button>').join("")+'</div>';
    }).join("");
    $$("#taxonomy-nav [data-category]").forEach(button=>button.addEventListener("click",()=>{state.category=button.dataset.category;state.view="skills";state.detail=null;render();}));
    if(!Object.values(counts).some(Boolean)) $("#taxonomy-nav").insertAdjacentHTML("beforeend",'<p class="muted">'+escapeHtml(t("noCategories"))+'</p>');
  }
  function resourceCards(){
    const q=state.query.trim().toLocaleLowerCase();
    let plugins=state.catalog.plugins, skills=state.catalog.skills;
    if(state.view==="plugins")skills=[];
    if(state.view==="skills")plugins=[];
    if(state.category){
      const node=categoryMap().get(state.category);
      const ids=new Set(state.catalog.aggregation.dimensions?.[node?.dimension]?.[state.category]?.skill_ids||[]);
      skills=skills.filter(s=>ids.has(s.id));plugins=[];
    }
    const match=(...values)=>!q||values.join(" ").toLocaleLowerCase().includes(q);
    plugins=plugins.filter(p=>match(p.id,p.name,p.display_name,p.description));
    skills=skills.filter(s=>match(s.id,s.name,s.description,s.plugin_id));
    const cards=[];
    for(const plugin of plugins)cards.push({kind:"plugin",id:plugin.id,title:pluginName(plugin),description:plugin.description||"",subtitle:plugin.id,meta:[(state.catalog.skills.filter(s=>s.plugin_id===plugin.id).length)+" "+t("skills")],item:plugin});
    const pluginsById=new Map(state.catalog.plugins.map(p=>[p.id,p]));
    for(const skill of skills){const p=pluginsById.get(skill.plugin_id);cards.push({kind:"skill",id:skill.id,title:skill.name,description:skill.description||"",subtitle:pluginName(p||{id:skill.plugin_id}),meta:approvedNames(skill).slice(0,3),item:skill});}
    cards.sort((a,b)=>a.title.localeCompare(b.title));
    return cards;
  }
  function renderResults(){
    const cards=resourceCards();$("#results").innerHTML=cards.map(card=>'<article class="resource-card" tabindex="0" role="link" data-kind="'+card.kind+'" data-id="'+escapeHtml(card.id)+'"><div class="card-top"><span class="resource-kind">'+(card.kind==="plugin"?"PLUGIN":"SKILL")+'</span><span class="resource-id">'+escapeHtml(card.subtitle)+'</span></div><h3>'+escapeHtml(card.title)+'</h3><p>'+escapeHtml(card.description)+'</p><div class="card-bottom">'+card.meta.map(x=>'<span class="chip">'+escapeHtml(x)+'</span>').join("")+'</div></article>').join("");
    $("#empty-state").hidden=cards.length!==0;$("#results").hidden=cards.length===0;
    $$("#results .resource-card").forEach(card=>{const open=()=>openDetail(card.dataset.kind,card.dataset.id);card.addEventListener("click",open);card.addEventListener("keydown",e=>{if(e.key==="Enter"||e.key===" "){e.preventDefault();open();}});});
    const node=state.category?categoryMap().get(state.category):null;
    $("#active-filter").hidden=!node;
    $("#active-filter").innerHTML=node?escapeHtml(nameOf(node))+' <button type="button" id="remove-filter">× '+escapeHtml(t("clearFilters"))+'</button>':"";
    $("#remove-filter")?.addEventListener("click",()=>{state.category=null;render();});
    $("#results-title").textContent=node?nameOf(node):state.query?t("searchResults"):state.view==="plugins"?"Plugins":state.view==="skills"?"Skills":t("allResources");
    $("#results-description").textContent=t("showing")+" "+cards.length+" "+t("results");
  }
  function renderDetail(){
    const panel=$("#detail-view"),layout=$(".content-layout"),hero=$(".hero"),stats=$("#stats");
    if(!state.detail){panel.hidden=true;layout.hidden=false;hero.hidden=false;stats.hidden=false;return;}
    panel.hidden=false;layout.hidden=true;hero.hidden=true;stats.hidden=true;
    const {kind,item}=state.detail;
    const plugin=kind==="plugin"?item:state.catalog.plugins.find(p=>p.id===item.plugin_id);
    const title=kind==="plugin"?pluginName(item):item.name;
    const source=kind==="plugin"?item.source_url:item.source_url;
    let html='<a href="#" class="detail-back" id="detail-back">← '+escapeHtml(t("back"))+'</a><header class="detail-header"><span class="resource-kind">'+(kind==="plugin"?"PLUGIN":"SKILL")+'</span><h1>'+escapeHtml(title)+'</h1><p class="detail-description">'+escapeHtml(item.description||"")+'</p><div class="detail-actions">';
    if(source)html+='<a class="action-link primary" href="'+escapeHtml(source)+'" target="_blank" rel="noreferrer">'+escapeHtml(t("openSource"))+'</a>';
    if(plugin?.source_url && kind==="skill")html+='<a class="action-link" href="'+escapeHtml(plugin.source_url)+'" target="_blank" rel="noreferrer">'+escapeHtml(t("viewPlugin"))+'</a>';
    html+='</div>';
    const cats=kind==="skill"?approvedNames(item):[];
    if(cats.length)html+='<div class="category-list">'+cats.map(c=>'<span class="chip">'+escapeHtml(c)+'</span>').join("")+'</div>';
    else if(kind==="skill")html+='<p class="muted">'+escapeHtml(t("unclassified"))+'</p>';
    html+='</header>';
    if(kind==="plugin"){
      const contained=state.catalog.skills.filter(s=>s.plugin_id===item.id);
      html+='<h2>'+escapeHtml(t("skillsInPlugin"))+' ('+contained.length+')</h2><div class="resource-grid">'+contained.map(s=>'<article class="resource-card" data-kind="skill" data-id="'+escapeHtml(s.id)+'"><span class="resource-kind">SKILL</span><h3>'+escapeHtml(s.name)+'</h3><p>'+escapeHtml(s.description||"")+'</p></article>').join("")+'</div>';
      if(!contained.length)html+='<p class="muted">'+escapeHtml(t("noSkills"))+'</p>';
    }else{
      const translation=item.translation;
      html+='<div class="language-tabs"><button class="language-tab '+(state.detailLang==="zh-CN"?"active":"")+'" data-detail-lang="zh-CN">'+escapeHtml(t("translation"))+'</button><button class="language-tab '+(state.detailLang==="en"?"active":"")+'" data-detail-lang="en">'+escapeHtml(t("english"))+'</button></div>';
      if(state.detailLang==="zh-CN" && translation){
        html+='<div class="translation-notice">'+escapeHtml(t("translationNote"))+'</div><div id="markdown-content" class="detail-body">'+escapeHtml(t("translation"))+'…</div>';
      }else if(state.detailLang==="zh-CN" && !translation){
        html+='<p class="muted">'+escapeHtml(t("noTranslation"))+'</p><div class="detail-body">'+markdownInline(item.description||"")+'</div>';
      }else{
        html+='<p class="muted">'+escapeHtml(t("source"))+'：'+escapeHtml(item.source_path||"")+'</p><div class="detail-body"><p>'+escapeHtml(item.description||"")+'</p><p><a href="'+escapeHtml(source||"#")+'" target="_blank" rel="noreferrer">'+escapeHtml(t("openSource"))+'</a></p></div>';
      }
    }
    panel.innerHTML=html;
    $("#detail-back").addEventListener("click",e=>{e.preventDefault();state.detail=null;history.pushState(null,"",location.pathname);render();});
    $$("[data-kind=skill]",panel).forEach(card=>card.addEventListener("click",()=>openDetail("skill",card.dataset.id)));
    $$("[data-detail-lang]",panel).forEach(button=>button.addEventListener("click",()=>{state.detailLang=button.dataset.detailLang;renderDetail();}));
    if(kind==="skill" && state.detailLang==="zh-CN" && item.translation){
      fetch("./"+item.translation.path).then(r=>{if(!r.ok)throw new Error("translation unavailable");return r.text();}).then(text=>{const target=$("#markdown-content");if(target)target.innerHTML=renderMarkdown(text);}).catch(()=>{const target=$("#markdown-content");if(target)target.textContent=t("noTranslation");});
    }
  }
  function openDetail(kind,id){
    const item=(kind==="plugin"?state.catalog.plugins:state.catalog.skills).find(x=>x.id===id);if(!item)return;
    state.detail={kind,item};state.detailLang="zh-CN";history.pushState(null,"",kind==="skill"?"?skill="+encodeURIComponent(id):"?plugin="+encodeURIComponent(id));renderDetail();window.scrollTo({top:0,behavior:"smooth"});
  }
  function render(){
    document.documentElement.lang=state.lang==="zh-CN"?"zh-CN":"en";
    $$("[data-i18n]").forEach(el=>{const key=el.dataset.i18n;el.textContent=t(key);});
    $$("[data-i18n-placeholder]").forEach(el=>el.placeholder=t(el.dataset.i18nPlaceholder));
    $("#language-toggle").textContent=state.lang==="zh-CN"?"EN":"中文";
    renderStats();renderTaxonomy();renderResults();renderDetail();
    $$(".view-button").forEach(button=>button.classList.toggle("active",button.dataset.view===state.view));
  }
  async function init(){
    try{
      const response=await fetch("./data/catalog.json");if(!response.ok)throw new Error("catalog unavailable");state.catalog=await response.json();
      const params=new URLSearchParams(location.search);
      const skill=params.get("skill"),plugin=params.get("plugin");
      $("#search-input").addEventListener("input",e=>{state.query=e.target.value;state.category=null;renderResults();});
      $("#search-input").addEventListener("keydown",e=>{if(e.key==="Escape"){e.target.value="";state.query="";renderResults();}});
      document.addEventListener("keydown",e=>{if((e.metaKey||e.ctrlKey)&&e.key.toLowerCase()==="k"){e.preventDefault();$("#search-input").focus();}});
      $("#language-toggle").addEventListener("click",()=>{state.lang=state.lang==="zh-CN"?"en":"zh-CN";render();});
      $$(".view-button").forEach(button=>button.addEventListener("click",()=>{state.view=button.dataset.view;state.category=null;render();}));
      $("#clear-filters").addEventListener("click",()=>{state.query="";state.category=null;state.view="all";$("#search-input").value="";render();});
      window.addEventListener("popstate",()=>{state.detail=null;const p=new URLSearchParams(location.search);const id=p.get("skill"),pid=p.get("plugin");if(id)openDetail("skill",id);else if(pid)openDetail("plugin",pid);else render();});
      render();
      if(skill)openDetail("skill",skill);else if(plugin)openDetail("plugin",plugin);
    }catch(error){$("#app").innerHTML='<div class="empty-state"><h3>网站数据暂时不可用</h3><p>'+escapeHtml(error.message)+'</p></div>';}
  }
  init();
})();