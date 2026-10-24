'use strict';
const requestButton=document.querySelector('#request-code'), form=document.querySelector('#code-form'), statusLine=document.querySelector('#login-status'), codeInput=document.querySelector('#code'), verifyButton=document.querySelector('#verify-code');
document.querySelector('#login-icon').innerHTML=radarIcon('briefcase');
let cooldown;
function message(text,error=false){statusLine.textContent=text;statusLine.classList.toggle('login-error',error);}
async function post(path,body){
  const response=await fetch(path,{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(body)});
  const result=await response.json();
  if(!response.ok)throw new Error(result.error||'Sign-in could not be completed.');
  return result;
}
requestButton.addEventListener('click',async()=>{
  requestButton.disabled=true;message('Sending a code through Telegram…');
  try{
    await post('/auth/request',{});form.hidden=false;codeInput.focus();
    message('Code sent. Check your Telegram message; the code expires in 5 minutes.');
    let left=60;requestButton.textContent='Resend in '+left+' s';
    clearInterval(cooldown);cooldown=setInterval(()=>{left--;requestButton.textContent=left?'Resend in '+left+' s':'Send another code';if(!left){clearInterval(cooldown);requestButton.disabled=false;}},1000);
  }catch(error){message(error.message,true);requestButton.disabled=false;}
});
form.addEventListener('submit',async event=>{
  event.preventDefault();verifyButton.disabled=true;message('Checking the code…');
  try{await post('/auth/verify',{code:codeInput.value.trim()});location.replace('/');}
  catch(error){message(error.message,true);verifyButton.disabled=false;}
});
fetch('/auth/session').then(r=>r.json()).then(session=>{
  if(session.authenticated)location.replace('/');
  else if(session.challenge){form.hidden=false;message('Enter your Telegram code or request a new one.');}
}).catch(()=>{});
fetch('/auth/config').then(r=>r.json()).then(config=>{
  document.querySelector('#brand-name').textContent=config.brand;
  document.querySelector('.login-access h2').textContent='Sign in with '+config.bot_name;
}).catch(()=>{});
