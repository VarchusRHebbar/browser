const { chromium } = require('playwright'); const { spawn } = require('child_process');
(async () => {
  const FPS=30, D=require("./timeline.json").D, N=FPS*D;
  const ff = spawn('ffmpeg',['-y','-loglevel','error','-f','image2pipe','-framerate',String(FPS),'-c:v','mjpeg','-i','-','-i','mix.wav',
    '-c:v','libx264','-preset','medium','-crf','18','-pix_fmt','yuv420p','-c:a','aac','-b:a','192k','-shortest','-movflags','+faststart','MEP_ink_wash_film_vo.mp4'],{stdio:['pipe','inherit','inherit']});
  const b = await chromium.launch(); const p = await b.newPage({viewport:{width:1920,height:1080}});
  p.on('pageerror', e => console.log('ERR', e.message));
  await p.goto('file://' + __dirname + '/film.html'); await p.evaluate(() => window.ready);
  for (let f=0; f<N; f++){
    const url = await p.evaluate(t => { render(t); return document.getElementById('c').toDataURL('image/jpeg', 0.93); }, f/FPS);
    const buf = Buffer.from(url.split(',')[1], 'base64');
    if (!ff.stdin.write(buf)) await new Promise(r => ff.stdin.once('drain', r));
    if (f%300===0) console.log('frame', f);
  }
  ff.stdin.end(); await new Promise(r => ff.on('close', r)); await b.close(); console.log('done');
})();
