'use strict';
const requestButton=document.querySelector('#request-code'), form=document.querySelector('#code-form'), statusLine=document.querySelector('#login-status'), codeInput=document.querySelector('#code'), verifyButton=document.querySelector('#verify-code');
document.querySelector('#login-icon').innerHTML=radarIcon('briefcase');
let cooldown;
function message(text,error=false){statusLine.textContent=text;statusLine.classList.toggle('login-error',error);}
async function post(path,body){
  const response=await fetch(path,{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(body)});
  const result=await response.json();
  if(!response.ok)throw new Error(result.error||'No se ha podido completar el acceso.');
  return result;
}
requestButton.addEventListener('click',async()=>{
  requestButton.disabled=true;message('Enviando el código con Telegram…');
  try{
    await post('/auth/request',{});form.hidden=false;codeInput.focus();
    message('Código enviado. Abre el mensaje de Telegram en Telegram; caduca en 5 minutos.');
    let left=60;requestButton.textContent='Reenviar en '+left+' s';
    clearInterval(cooldown);cooldown=setInterval(()=>{left--;requestButton.textContent=left?'Reenviar en '+left+' s':'Enviar otro código';if(!left){clearInterval(cooldown);requestButton.disabled=false;}},1000);
  }catch(error){message(error.message,true);requestButton.disabled=false;}
});
form.addEventListener('submit',async event=>{
  event.preventDefault();verifyButton.disabled=true;message('Comprobando el código…');
  try{await post('/auth/verify',{code:codeInput.value.trim()});location.replace('/');}
  catch(error){message(error.message,true);verifyButton.disabled=false;}
});
fetch('/auth/session').then(r=>r.json()).then(session=>{
  if(session.authenticated)location.replace('/');
  else if(session.challenge){form.hidden=false;message('Introduce el código de Telegram o solicita uno nuevo.');}
}).catch(()=>{});
fetch('/auth/config').then(r=>r.json()).then(config=>{
  document.querySelector('#brand-name').textContent=config.brand;
  document.querySelector('.login-access h2').textContent='Entra con '+config.bot_name;
}).catch(()=>{});
