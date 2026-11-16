/* Gerador de .zip mínimo (sem compressão, método «store»): as cartinhas já são PNG, então comprimir de novo não ganha nada.
   ZipSimples.criar([{ nome: 'Equipe 3/01-cartinha.png', dados: Blob|Uint8Array }]) → Promise<Blob>. Nomes em UTF-8. Sem dependências. */
(function () {
  var T = new Uint32Array(256);
  for (var n = 0; n < 256; n++) { var c = n; for (var k = 0; k < 8; k++) c = (c & 1) ? (0xEDB88320 ^ (c >>> 1)) : (c >>> 1); T[n] = c >>> 0; }
  function crc32(u8) { var c = 0xFFFFFFFF; for (var i = 0; i < u8.length; i++) c = T[(c ^ u8[i]) & 255] ^ (c >>> 8); return (c ^ 0xFFFFFFFF) >>> 0; }
  function dos(d) { return { t: (d.getHours() << 11) | (d.getMinutes() << 5) | (d.getSeconds() >> 1), d: ((d.getFullYear() - 1980) << 9) | ((d.getMonth() + 1) << 5) | d.getDate() }; }
  function cab(tam) { var b = new DataView(new ArrayBuffer(tam)); return { v: b, u8: new Uint8Array(b.buffer) }; }
  function criar(arquivos) {
    var enc = new TextEncoder(), agora = dos(new Date()), partes = [], central = [], pos = 0;
    return arquivos.reduce(function (cadeia, f) {
      return cadeia.then(function () {
        var dado = f.dados instanceof Blob ? f.dados.arrayBuffer().then(function (b) { return new Uint8Array(b); }) : Promise.resolve(f.dados);
        return dado.then(function (u8) {
          var nome = enc.encode(f.nome), crc = crc32(u8), h = cab(30);
          h.v.setUint32(0, 0x04034b50, true); h.v.setUint16(4, 20, true); h.v.setUint16(6, 0x0800, true); h.v.setUint16(8, 0, true);
          h.v.setUint16(10, agora.t, true); h.v.setUint16(12, agora.d, true); h.v.setUint32(14, crc, true); h.v.setUint32(18, u8.length, true); h.v.setUint32(22, u8.length, true);
          h.v.setUint16(26, nome.length, true); h.v.setUint16(28, 0, true);
          partes.push(h.u8, nome, u8);
          var c = cab(46);
          c.v.setUint32(0, 0x02014b50, true); c.v.setUint16(4, 20, true); c.v.setUint16(6, 20, true); c.v.setUint16(8, 0x0800, true); c.v.setUint16(10, 0, true);
          c.v.setUint16(12, agora.t, true); c.v.setUint16(14, agora.d, true); c.v.setUint32(16, crc, true); c.v.setUint32(20, u8.length, true); c.v.setUint32(24, u8.length, true);
          c.v.setUint16(28, nome.length, true); c.v.setUint32(42, pos, true);
          central.push(c.u8, nome);
          pos += 30 + nome.length + u8.length;
        });
      });
    }, Promise.resolve()).then(function () {
      var tamCentral = central.reduce(function (t, p) { return t + p.length; }, 0), fim = cab(22);
      fim.v.setUint32(0, 0x06054b50, true); fim.v.setUint16(8, arquivos.length, true); fim.v.setUint16(10, arquivos.length, true);
      fim.v.setUint32(12, tamCentral, true); fim.v.setUint32(16, pos, true);
      return new Blob(partes.concat(central, [fim.u8]), { type: 'application/zip' });
    });
  }
  window.ZipSimples = { criar: criar };
})();
