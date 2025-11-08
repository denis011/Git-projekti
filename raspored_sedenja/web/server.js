import express from 'express';
import fetch from 'node-fetch';
const app = express();
const port = process.env.WEB_PORT || 3000;
app.use(express.json());
app.use(express.urlencoded({ extended: true }));

function html(body){
  return `<!doctype html>
  <html><head>
    <meta charset="utf-8"/>
    <title>SeatApp MVP</title>
    <style>
      body{font-family: system-ui, sans-serif; max-width: 900px; margin: 2rem auto; padding: 0 1rem;}
      nav a{margin-right: 12px;}
      .seat{margin:4px;padding:8px;border:1px solid #ccc;display:inline-block;border-radius:6px;}
      .card{border:1px solid #ddd; padding:12px; border-radius:8px; margin:12px 0;}
      pre{background:#f6f6f6; padding:8px; border-radius:6px;}
      input,button{padding:8px;margin:4px;}
    </style>
  </head><body>
    <nav>
      <a href="/">Home</a>
      <a href="/map">Mapa</a>
      <a href="/reports">Izveštaji</a>
      <a href="/login">Login</a>
      <a href="/logout">Logout</a>
    </nav>
    ${body}
  </body></html>`;
}

app.get('/', (req,res)=>{
  res.send(html(`<h1>SeatApp MVP (Local Auth)</h1><p>Ulogujte se da biste videli mapu i izveštaje.</p>`));
});

app.get('/login', (req,res)=>{
  res.send(html(`
  <h2>Login</h2>
  <form method="post" action="/login">
    <input name="username" placeholder="username" required />
    <input name="password" type="password" placeholder="password" required />
    <button type="submit">Login</button>
  </form>
  <div class="card"><b>Default admin:</b> <code>admin / Admin#12345</code> (promenite odmah)</div>
  `));
});

app.post('/login', async (req,res)=>{
  try{
    const r = await fetch('http://nginx/api/login', {
      method:'POST',
      headers:{'Content-Type':'application/json'},
      body: JSON.stringify({username:req.body.username, password:req.body.password}),
    });
    if(!r.ok){
      const t = await r.text();
      return res.status(401).send(html(`<h2>Login failed</h2><pre>${t}</pre><a href="/login">Back</a>`));
    }
    const setCookie = r.headers.get('set-cookie');
    if(setCookie) res.setHeader('set-cookie', setCookie.replace(/; Path=\/?/i, '; Path=/'));
    res.redirect('/map');
  }catch(e){
    res.status(500).send(html(`<h2>Error</h2><pre>${e.toString()}</pre>`));
  }
});

app.get('/logout', async (req,res)=>{
  await fetch('http://nginx/api/logout', {method:'POST'});
  res.setHeader('set-cookie', 'seatapp_session=; Max-Age=0; Path=/');
  res.redirect('/');
});

app.get('/map', async (req,res)=>{
  try{
    const me = await fetch('http://nginx/api/me', {headers:{cookie:req.headers.cookie||''}});
    if(!me.ok) return res.redirect('/login');
    const meJson = await me.json();
    const floors = await (await fetch('http://nginx/api/floors', {headers:{cookie:req.headers.cookie||''}})).json();
    const floorId = floors[0]?.id || 1;
    const seats = await (await fetch(`http://nginx/api/seats?floorId=${floorId}`, {headers:{cookie:req.headers.cookie||''}})).json();
    res.send(html(`
      <h2>Mapa — ${floors[0]?.name||'Floor 1'}</h2>
      <div>${seats.map(s=>`<div class="seat">${s.code}</div>`).join('')}</div>
      <div class="card"><b>Korisnik:</b> ${meJson.name} (${meJson.upn})</div>
    `));
  }catch(e){
    res.status(500).send(html(`<h2>Error</h2><pre>${e.toString()}</pre>`));
  }
});

app.get('/reports', async (req,res)=>{
  try{
    const me = await fetch('http://nginx/api/me', {headers:{cookie:req.headers.cookie||''}});
    if(!me.ok) return res.redirect('/login');
    const [w,m,y] = await Promise.all([
      fetch('http://nginx/api/reports/weekly', {headers:{cookie:req.headers.cookie||''}}).then(r=>r.json()),
      fetch('http://nginx/api/reports/monthly', {headers:{cookie:req.headers.cookie||''}}).then(r=>r.json()),
      fetch('http://nginx/api/reports/yearly', {headers:{cookie:req.headers.cookie||''}}).then(r=>r.json()),
    ]);
    res.send(html(`
      <h2>Izveštaji (moji)</h2>
      <div class="card"><h3>Nedeljni</h3><pre>${JSON.stringify(w, null, 2)}</pre></div>
      <div class="card"><h3>Mesečni</h3><pre>${JSON.stringify(m, null, 2)}</pre></div>
      <div class="card"><h3>Godišnji</h3><pre>${JSON.stringify(y, null, 2)}</pre></div>
      <p>(UI grafici su placeholder; API je spreman.)</p>
    `));
  }catch(e){
    res.status(500).send(html(`<h2>Error</h2><pre>${e.toString()}</pre>`));
  }
});

app.listen(port, () => console.log('SeatApp web listening on', port));
