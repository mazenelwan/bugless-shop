/* Shared catalog source for the shop and the reusable product page. */
(function (window) {
  var rows = [
    ['shirts-01',"Men's Shirts",'Man Long Sleeve Shirt',459,'https://dfcdn.defacto.com.tr/6/F8314AX_25AU_KH244_01_01.jpg'],
    ['shirts-02',"Men's Shirts",'Man Long Sleeve Shirt',459,'https://dfcdn.defacto.com.tr/6/F6342AX_25AU_BG721_01_01.jpg'],
    ['shirts-03',"Men's Shirts",'Man Long Sleeve Shirt',459,'https://dfcdn.defacto.com.tr/6/F6342AX_25AU_BK81_01_01.jpg'],
    ['shirts-04',"Men's Shirts",'Man Long Sleeve Shirt',459,'https://dfcdn.defacto.com.tr/6/F6342AX_25AU_BR496_01_01.jpg'],
    ['jacket-01','Jacket','Regular fit hooded zippered waterproof jacket',2200,'https://dfcdn.defacto.com.tr/6/D5977AX_25SP_BG73_01_01.jpg'],
    ['jacket-02','Jacket','Slim Fit Stand up Called zippered jacket',3000,'https://dfcdn.defacto.com.tr/6/C6214AX_25AU_GR158_01_01.jpg'],
    ['jacket-03','Jacket','Oversize Fit Velvet Puffer jacket',4999,'https://dfcdn.defacto.com.tr/6/D7534AX_25AU_BK27_01_01.jpg'],
    ['jacket-04','Jacket','Slim Fit Stand up Called zippered jacket',3000,'https://dfcdn.defacto.com.tr/6/E8819AX_25AU_NV175_01_02.jpg'],
    ['pants-01','Pants','Regular Fit Flexible Leg Cargo Sweatpants',999,'https://m.media-amazon.com/images/I/6121rM3990L.AC_SX679.jpg'],
    ['pants-02','Pants','Slim Fit Double Pocket Standard Leg Sports Joggers',999,'https://m.media-amazon.com/images/I/51M89g3N4oL.AC_SX679.jpg'],
    ['pants-03','Pants','Relax Fit Linen Look Straight Leg Cotton Trousers',999,'https://m.media-amazon.com/images/I/615RRAT49wL.AC_SX679.jpg'],
    ['pants-04','Pants','Slim Fit Double Pocket Standard Leg Sports Joggers',999,'https://m.media-amazon.com/images/I/51JeL7CaFeL.AC_SX679.jpg'],
    ['tshirts-01','T-Shirts','Oversize T-Shirt',499,'https://m.media-amazon.com/images/I/71BhTPORZuL.AC_SX522.jpg'],
    ['tshirts-02','T-Shirts','Oversize T-Shirt',499,'https://m.media-amazon.com/images/I/71ayg6Ml9cL.AC_SX522.jpg'],
    ['tshirts-03','T-Shirts','Oversize T-Shirt',499,'https://m.media-amazon.com/images/I/71c7Hb3Ya7L.AC_SX679.jpg'],
    ['tshirts-04','T-Shirts','Oversize T-Shirt',499,'https://m.media-amazon.com/images/I/71jPSDNxBjL.AC_SX522.jpg'],
    ['polo-01','Polo','polo Shirt',549,'https://dfcdn.defacto.com.tr/6/D7932AX_25SP_NV135_01_02.jpg'],
    ['polo-02','Polo','polo Shirt',549,'https://dfcdn.defacto.com.tr/6/E2888AX_25SP_BK27_01_01.jpg'],
    ['polo-03','Polo','polo Shirt',549,'https://dfcdn.defacto.com.tr/6/E1209AX_25SM_GR265_01_01.jpg'],
    ['polo-04','Polo','polo Shirt',549,'https://dfcdn.defacto.com.tr/6/E2633AX_25SM_GN1113_01_03.jpg'],
    ['shoes-01','Shoes','Plain Toe Blucher',450,'https://pronto-eg.com/cdn/shop/products/0212-1_copy_1b5e2b70-5888-4aa7-b592-b143bd3ba487.jpg?v=1748425483&width=640'],
    ['shoes-02','Shoes','Chelsea Boot',900,'https://pronto-eg.com/cdn/shop/products/15052-1-5_copy_27f4143b-53f1-458f-b0fa-1365141d6f4a.jpg?v=1671282625&width=640'],
    ['shoes-03','Shoes','Oxford Limit',550,'https://pronto-eg.com/cdn/shop/products/0301-5-5_copy_3982c7d4-783d-4b37-afe3-41b4be13e965.jpg?v=1671281262&width=640'],
    ['shoes-04','Shoes','Rock',700,'https://pronto-eg.com/cdn/shop/products/15010-1-5_copy_c7c372b2-2d4e-429e-87da-f61e0eb7d72e.jpg?v=1671282591&width=640']
  ];
  window.BF_PRODUCTS = rows.map(function (row) {
    return { id: row[0], category: row[1], name: row[2], price: row[3], image: row[4], images: [row[4]], colors: [], sizes: [], description: 'A ' + row[1].replace(/s$/, '').toLowerCase() + ' from the BUGLESS FIT collection.' };
  });
  window.BF_PRODUCT_BY_ID = function (id) { return window.BF_PRODUCTS.filter(function (p) { return p.id === id; })[0]; };
})(window);
