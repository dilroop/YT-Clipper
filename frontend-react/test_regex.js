const fullText = 'cherry salt, that\\'s the one is my favorite. Try element, see how you feel? Elements got a world class customer service team. Okay, so what happened? Like, walk us through it.';
const chunks = [];
const splitRegex = /([.?!]+(?:\s+|$))/;
const parts = fullText.split(splitRegex);
for(let i=0; i<parts.length; i+=2) {
  const text = parts[i] || '';
  const sep = parts[i+1] || '';
  if(text+sep) chunks.push(text+sep);
}
chunks.forEach((c) => {
  console.log('Chunk: [' + c + '], isQuestion=' + c.includes('?'));
});
