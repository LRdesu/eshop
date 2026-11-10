-- ============================================================
-- 模拟电商平台 数据库 Schema  v0.2（18 张表）
-- 库名：eshop  |  字符集：utf8mb4  |  引擎：InnoDB
-- 说明：覆盖完整购物生命周期（加购/结算/支付/履约/收货/售后/复购）
-- 导入方式：mysql -uroot -p eshop < schema.sql  或  pymysql 执行本文件
-- ============================================================

SET NAMES utf8mb4;
SET FOREIGN_KEY_CHECKS = 0;

DROP DATABASE IF EXISTS eshop;
CREATE DATABASE eshop DEFAULT CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci;
USE eshop;

-- ----------------------------------------------------------
-- 1. 用户表
-- ----------------------------------------------------------
CREATE TABLE users (
  id            INT PRIMARY KEY AUTO_INCREMENT COMMENT '买家ID',
  username      VARCHAR(50)  NOT NULL UNIQUE COMMENT '登录名',
  password_hash VARCHAR(100) NOT NULL COMMENT 'bcrypt 密码哈希',
  phone         VARCHAR(20)  COMMENT '手机号',
  nickname      VARCHAR(50)  COMMENT '昵称',
  points        INT NOT NULL DEFAULT 0 COMMENT '积分余额（冗余，流水见 points_log）',
  created_at    DATETIME DEFAULT CURRENT_TIMESTAMP COMMENT '注册时间'
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='买家账号';

-- ----------------------------------------------------------
-- 2. 收货地址表
-- ----------------------------------------------------------
CREATE TABLE addresses (
  id         INT PRIMARY KEY AUTO_INCREMENT COMMENT '地址ID',
  user_id    INT NOT NULL COMMENT '买家ID',
  receiver   VARCHAR(50) NOT NULL COMMENT '收件人',
  phone      VARCHAR(20) NOT NULL COMMENT '收件电话',
  province   VARCHAR(50) COMMENT '省',
  city       VARCHAR(50) COMMENT '市',
  district   VARCHAR(50) COMMENT '区',
  detail     VARCHAR(200) NOT NULL COMMENT '详细地址',
  is_default TINYINT DEFAULT 0 COMMENT '是否默认 1是0否',
  created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
  KEY idx_addr_user (user_id),
  CONSTRAINT fk_addr_user FOREIGN KEY (user_id) REFERENCES users(id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='收货地址';

-- ----------------------------------------------------------
-- 3. 商品 SPU 表
-- ----------------------------------------------------------
CREATE TABLE products (
  id          INT PRIMARY KEY AUTO_INCREMENT COMMENT '商品SPU ID',
  name        VARCHAR(100) NOT NULL COMMENT '商品名',
  description TEXT COMMENT '描述',
  category    VARCHAR(50) COMMENT '分类',
  cover       VARCHAR(255) COMMENT '主图URL',
  gallery     TEXT COMMENT '详情页图URL(逗号分隔)',
  created_at  DATETIME DEFAULT CURRENT_TIMESTAMP,
  KEY idx_prod_cat (category)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='商品SPU';

-- ----------------------------------------------------------
-- 4. 商品 SKU 表（实时价格 / 库存）
-- ----------------------------------------------------------
CREATE TABLE skus (
  id        INT PRIMARY KEY AUTO_INCREMENT COMMENT 'SKU ID',
  product_id INT NOT NULL COMMENT '商品ID',
  spec      VARCHAR(100) NOT NULL COMMENT '规格 如 颜色:红/尺寸:M',
  price     DECIMAL(10,2) NOT NULL COMMENT '单价',
  stock     INT NOT NULL DEFAULT 0 COMMENT '库存',
  image     VARCHAR(255) COMMENT 'SKU图URL',
  created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
  KEY idx_sku_prod (product_id),
  CONSTRAINT fk_sku_prod FOREIGN KEY (product_id) REFERENCES products(id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='商品SKU';

-- ----------------------------------------------------------
-- 5. 评价表
-- ----------------------------------------------------------
CREATE TABLE reviews (
  id         INT PRIMARY KEY AUTO_INCREMENT COMMENT '评价ID',
  order_id   INT NOT NULL COMMENT '订单ID',
  sku_id     INT NOT NULL COMMENT 'SKU ID',
  user_id    INT NOT NULL COMMENT '评价人',
  rating     TINYINT NOT NULL COMMENT '星级 1-5',
  content    TEXT COMMENT '评价内容',
  images     VARCHAR(512) COMMENT '图URL(逗号分隔)',
  created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
  KEY idx_review_sku (sku_id),
  KEY idx_review_order (order_id),
  CONSTRAINT fk_review_order FOREIGN KEY (order_id) REFERENCES orders(id),
  CONSTRAINT fk_review_sku FOREIGN KEY (sku_id) REFERENCES skus(id),
  CONSTRAINT fk_review_user FOREIGN KEY (user_id) REFERENCES users(id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='商品评价';

-- ----------------------------------------------------------
-- 6. 购物车表
-- ----------------------------------------------------------
CREATE TABLE cart_items (
  id        INT PRIMARY KEY AUTO_INCREMENT COMMENT '购物车项ID',
  user_id   INT NOT NULL COMMENT '买家ID',
  sku_id    INT NOT NULL COMMENT 'SKU ID',
  quantity  INT NOT NULL DEFAULT 1 COMMENT '数量',
  created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
  KEY idx_cart_user (user_id),
  CONSTRAINT fk_cart_user FOREIGN KEY (user_id) REFERENCES users(id),
  CONSTRAINT fk_cart_sku FOREIGN KEY (sku_id) REFERENCES skus(id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='购物车';

-- ----------------------------------------------------------
-- 7. 订单主表（金额口径 + 时间字段）
-- ----------------------------------------------------------
CREATE TABLE orders (
  id               INT PRIMARY KEY AUTO_INCREMENT COMMENT '订单ID',
  order_no         VARCHAR(32) NOT NULL UNIQUE COMMENT '订单号',
  user_id          INT NOT NULL COMMENT '买家ID',
  address_id       INT NOT NULL COMMENT '地址ID',
  goods_amount     DECIMAL(10,2) NOT NULL DEFAULT 0 COMMENT '商品行金额合计',
  discount_amount  DECIMAL(10,2) NOT NULL DEFAULT 0 COMMENT '优惠金额（券）',
  points_used      INT NOT NULL DEFAULT 0 COMMENT '淘金币抵扣所用币数',
  points_discount  DECIMAL(10,2) NOT NULL DEFAULT 0 COMMENT '金币抵扣金额',
  shipping_fee     DECIMAL(10,2) NOT NULL DEFAULT 0 COMMENT '运费',
  pay_amount       DECIMAL(10,2) NOT NULL DEFAULT 0 COMMENT '实付=商品-优惠-金币+运费',
  coupon_id        INT COMMENT '使用的商品券(user_coupons.id)',
  shipping_coupon_id INT COMMENT '使用的运费券(user_coupons.id)',
  pay_status       TINYINT NOT NULL DEFAULT 0 COMMENT '0未付 1已付 2已关闭(超时)',
  order_status     TINYINT NOT NULL DEFAULT 0 COMMENT '0待付款 1待发货 2已发货 3已签收 4已完成 5已取消',
  expire_at        DATETIME COMMENT '支付截止时间(默认30分钟)',
  paid_at          DATETIME COMMENT '付款时间',
  confirmed_at     DATETIME COMMENT '确认收货时间',
  auto_confirm_at  DATETIME COMMENT '自动确认收货时间',
  created_at       DATETIME DEFAULT CURRENT_TIMESTAMP,
  KEY idx_order_user (user_id),
  KEY idx_order_no (order_no),
  CONSTRAINT fk_order_user FOREIGN KEY (user_id) REFERENCES users(id),
  CONSTRAINT fk_order_addr FOREIGN KEY (address_id) REFERENCES addresses(id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='订单主表';

-- ----------------------------------------------------------
-- 8. 订单明细表（分摊口径）
-- ----------------------------------------------------------
CREATE TABLE order_items (
  id             INT PRIMARY KEY AUTO_INCREMENT COMMENT '明细ID',
  order_id       INT NOT NULL COMMENT '订单ID',
  sku_id         INT NOT NULL COMMENT 'SKU ID',
  product_id     INT NOT NULL COMMENT '商品ID',
  quantity       INT NOT NULL COMMENT '数量',
  price          DECIMAL(10,2) NOT NULL COMMENT '下单时单价快照',
  goods_amount   DECIMAL(10,2) NOT NULL DEFAULT 0 COMMENT '行金额=price*quantity',
  discount_amount DECIMAL(10,2) NOT NULL DEFAULT 0 COMMENT '该行分摊到的优惠额',
  pay_amount     DECIMAL(10,2) NOT NULL DEFAULT 0 COMMENT '该行实付=goods_amount-discount_amount',
  KEY idx_oi_order (order_id),
  CONSTRAINT fk_oi_order FOREIGN KEY (order_id) REFERENCES orders(id),
  CONSTRAINT fk_oi_sku FOREIGN KEY (sku_id) REFERENCES skus(id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='订单明细';

-- ----------------------------------------------------------
-- 9. 运单表
-- ----------------------------------------------------------
CREATE TABLE shipments (
  id          INT PRIMARY KEY AUTO_INCREMENT COMMENT '运单ID',
  order_id    INT NOT NULL UNIQUE COMMENT '订单ID',
  carrier     VARCHAR(50) COMMENT '快递公司',
  tracking_no VARCHAR(50) COMMENT '运单号',
  ship_status TINYINT NOT NULL DEFAULT 0 COMMENT '0待发货 1已发货 2仓库拣货 3已揽收 4运输中 5派送中 6已签收',
  from_city   VARCHAR(50) COMMENT '发货城市（仓库所在，统一上海）',
  to_city     VARCHAR(50) COMMENT '收货城市（统一南京）',
  shipped_at  DATETIME COMMENT '发货时间',
  created_at  DATETIME DEFAULT CURRENT_TIMESTAMP,
  CONSTRAINT fk_ship_order FOREIGN KEY (order_id) REFERENCES orders(id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='运单';

-- ----------------------------------------------------------
-- 10. 物流轨迹表
-- ----------------------------------------------------------
CREATE TABLE shipment_traces (
  id          INT PRIMARY KEY AUTO_INCREMENT COMMENT '轨迹ID',
  shipment_id INT NOT NULL COMMENT '运单ID',
  node        VARCHAR(50) COMMENT '节点状态',
  city        VARCHAR(50) COMMENT '发生城市',
  description VARCHAR(255) COMMENT '描述',
  occurred_at DATETIME COMMENT '发生时间',
  KEY idx_trace_ship (shipment_id),
  CONSTRAINT fk_trace_ship FOREIGN KEY (shipment_id) REFERENCES shipments(id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='物流轨迹';

-- ----------------------------------------------------------
-- 11. 优惠券模板表
-- ----------------------------------------------------------
CREATE TABLE coupons (
  id         INT PRIMARY KEY AUTO_INCREMENT COMMENT '券模板ID',
  name       VARCHAR(100) NOT NULL COMMENT '券名称',
  type       VARCHAR(20) NOT NULL COMMENT 'FULL满减 DISCOUNT折扣 SHIPPING运费',
  threshold  DECIMAL(10,2) NOT NULL DEFAULT 0 COMMENT '使用门槛(满X,0无门槛)',
  value      DECIMAL(10,2) NOT NULL COMMENT '满减额/折扣率(0.9)/运费减免',
  scope      VARCHAR(20) NOT NULL DEFAULT 'ALL' COMMENT 'ALL全场 CATEGORY分类 PRODUCT指定商品',
  scope_value VARCHAR(100) COMMENT '分类名或商品id列表(scope=ALL时为空)',
  valid_from DATETIME COMMENT '生效时间',
  valid_to   DATETIME COMMENT '失效时间',
  total      INT NOT NULL DEFAULT 0 COMMENT '发放总量',
  per_limit  INT NOT NULL DEFAULT 1 COMMENT '每人限领',
  created_at DATETIME DEFAULT CURRENT_TIMESTAMP
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='优惠券模板';

-- ----------------------------------------------------------
-- 12. 用户持券表
-- ----------------------------------------------------------
CREATE TABLE user_coupons (
  id          INT PRIMARY KEY AUTO_INCREMENT COMMENT '持券ID',
  user_id     INT NOT NULL COMMENT '买家ID',
  coupon_id   INT NOT NULL COMMENT '券模板ID',
  status      TINYINT NOT NULL DEFAULT 0 COMMENT '0未用 1已用 2作废/过期',
  order_id    INT COMMENT '绑定订单',
  obtained_at DATETIME DEFAULT CURRENT_TIMESTAMP COMMENT '领取时间',
  used_at     DATETIME COMMENT '使用时间',
  KEY idx_uc_user (user_id),
  CONSTRAINT fk_uc_user FOREIGN KEY (user_id) REFERENCES users(id),
  CONSTRAINT fk_uc_coupon FOREIGN KEY (coupon_id) REFERENCES coupons(id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='用户持券';

-- ----------------------------------------------------------
-- 13. 运费规则表
-- ----------------------------------------------------------
CREATE TABLE shipping_fees (
  id     INT PRIMARY KEY AUTO_INCREMENT COMMENT '运费规则ID',
  region VARCHAR(50) NOT NULL COMMENT '地区(省内/省外)',
  fee    DECIMAL(10,2) NOT NULL COMMENT '运费',
  UNIQUE KEY uk_region (region)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='运费规则';

-- ----------------------------------------------------------
-- 14. 支付单表
-- ----------------------------------------------------------
CREATE TABLE payments (
  id           INT PRIMARY KEY AUTO_INCREMENT COMMENT '支付单ID',
  payment_no   VARCHAR(40) NOT NULL UNIQUE COMMENT '支付流水号(幂等键)',
  order_id     INT NOT NULL COMMENT '订单ID',
  user_id      INT NOT NULL COMMENT '买家ID',
  channel      VARCHAR(20) NOT NULL DEFAULT 'BALANCE' COMMENT 'BALANCE/WECHAT/ALIPAY',
  amount       DECIMAL(10,2) NOT NULL COMMENT '支付金额',
  status       TINYINT NOT NULL DEFAULT 0 COMMENT '0待付 1成功 2关闭/失败',
  expire_at    DATETIME COMMENT '支付截止',
  paid_at      DATETIME COMMENT '付款时间',
  callback_data TEXT COMMENT '回调原始数据',
  created_at   DATETIME DEFAULT CURRENT_TIMESTAMP,
  KEY idx_pay_order (order_id),
  CONSTRAINT fk_pay_order FOREIGN KEY (order_id) REFERENCES orders(id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='支付单';

-- ----------------------------------------------------------
-- 15. 退款单表
-- ----------------------------------------------------------
CREATE TABLE refunds (
  id           INT PRIMARY KEY AUTO_INCREMENT COMMENT '退款单ID',
  refund_no    VARCHAR(40) NOT NULL UNIQUE COMMENT '退款流水号',
  after_sale_id INT NOT NULL COMMENT '售后单ID',
  payment_no   VARCHAR(40) COMMENT '原支付流水号',
  user_id      INT NOT NULL COMMENT '买家ID',
  amount       DECIMAL(10,2) NOT NULL COMMENT '退款金额',
  channel      VARCHAR(20) COMMENT '原路渠道',
  status       TINYINT NOT NULL DEFAULT 0 COMMENT '0待退 1成功 2失败',
  reason       VARCHAR(255) COMMENT '退款原因',
  created_at   DATETIME DEFAULT CURRENT_TIMESTAMP,
  finished_at  DATETIME COMMENT '退款完成时间',
  KEY idx_refund_as (after_sale_id),
  CONSTRAINT fk_refund_as FOREIGN KEY (after_sale_id) REFERENCES after_sales(id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='退款单';

-- ----------------------------------------------------------
-- 16. 售后单表
-- ----------------------------------------------------------
CREATE TABLE after_sales (
  id          INT PRIMARY KEY AUTO_INCREMENT COMMENT '售后单ID',
  as_no       VARCHAR(40) NOT NULL UNIQUE COMMENT '售后单号',
  order_id    INT NOT NULL COMMENT '订单ID',
  user_id     INT NOT NULL COMMENT '买家ID',
  type        VARCHAR(20) NOT NULL COMMENT 'REFUND仅退款 RETURN退货退款 EXCHANGE换货',
  sku_id      INT NOT NULL COMMENT 'SKU ID',
  quantity    INT NOT NULL COMMENT '售后数量',
  reason      VARCHAR(255) COMMENT '原因',
  refund_amount DECIMAL(10,2) NOT NULL DEFAULT 0 COMMENT '退款额(按分摊比例算)',
  status      TINYINT NOT NULL DEFAULT 0 COMMENT '0申请中 1同意 2退款中 3已完成 4拒绝',
  created_at  DATETIME DEFAULT CURRENT_TIMESTAMP,
  handled_at  DATETIME COMMENT '处理时间',
  KEY idx_as_order (order_id),
  CONSTRAINT fk_as_order FOREIGN KEY (order_id) REFERENCES orders(id),
  CONSTRAINT fk_as_sku FOREIGN KEY (sku_id) REFERENCES skus(id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='售后单';

-- ----------------------------------------------------------
-- 17. 积分流水表
-- ----------------------------------------------------------
CREATE TABLE points_log (
  id          INT PRIMARY KEY AUTO_INCREMENT COMMENT '积分流水ID',
  user_id     INT NOT NULL COMMENT '买家ID',
  point_delta INT NOT NULL COMMENT '积分变动(正加负减)',
  type        VARCHAR(20) NOT NULL COMMENT 'EARN获赠 SPEND消费 REFUND退回',
  ref_order_no VARCHAR(32) COMMENT '关联订单号',
  remark      VARCHAR(255) COMMENT '备注',
  created_at  DATETIME DEFAULT CURRENT_TIMESTAMP,
  KEY idx_pl_user (user_id),
  CONSTRAINT fk_pl_user FOREIGN KEY (user_id) REFERENCES users(id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='积分流水';

-- ----------------------------------------------------------
-- 18. 用户标签表（RFM 分层）
-- ----------------------------------------------------------
CREATE TABLE user_tags (
  id          INT PRIMARY KEY AUTO_INCREMENT COMMENT '标签ID',
  user_id     INT NOT NULL UNIQUE COMMENT '买家ID',
  rfm_level   VARCHAR(20) COMMENT 'RFM分层(重要价值客户/新客/流失...)',
  rfm_score   VARCHAR(20) COMMENT '分值组合 R1F2M3',
  recency     INT COMMENT '最近下单距今天数',
  frequency   INT COMMENT '累计订单数',
  monetary    DECIMAL(10,2) COMMENT '累计实付金额',
  tags        VARCHAR(512) COMMENT '其他标签(逗号分隔)',
  updated_at  DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  CONSTRAINT fk_tag_user FOREIGN KEY (user_id) REFERENCES users(id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='用户标签(RFM)';

SET FOREIGN_KEY_CHECKS = 1;

-- ----------------------------------------------------------
-- 19. 退货逆向物流表
-- ----------------------------------------------------------
CREATE TABLE return_shipments (
  id              INT PRIMARY KEY AUTO_INCREMENT COMMENT '退货运单ID',
  after_sale_id   INT NOT NULL UNIQUE COMMENT '售后单ID',
  carrier         VARCHAR(50) COMMENT '快递公司',
  tracking_no     VARCHAR(50) COMMENT '退货运单号',
  return_status   TINYINT NOT NULL DEFAULT 0 COMMENT '0待寄回 1已揽收 2运输中 3已签收(入库)',
  from_city       VARCHAR(50) COMMENT '寄出城市（买家，统一南京）',
  to_city         VARCHAR(50) COMMENT '退货目的地（仓库，统一上海）',
  shipped_at      DATETIME COMMENT '寄出时间',
  received_at     DATETIME COMMENT '入库/签收时间',
  created_at      DATETIME DEFAULT CURRENT_TIMESTAMP,
  CONSTRAINT fk_ret_as FOREIGN KEY (after_sale_id) REFERENCES after_sales(id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='退货逆向物流';

-- ----------------------------------------------------------
-- 20. 退货物流轨迹表
-- ----------------------------------------------------------
CREATE TABLE return_traces (
  id          INT PRIMARY KEY AUTO_INCREMENT COMMENT '轨迹ID',
  return_shipment_id INT NOT NULL COMMENT '退货运单ID',
  node        VARCHAR(50) COMMENT '节点状态',
  city        VARCHAR(50) COMMENT '发生城市',
  description VARCHAR(255) COMMENT '描述',
  occurred_at DATETIME COMMENT '发生时间',
  KEY idx_ret_trace (return_shipment_id),
  CONSTRAINT fk_ret_trace FOREIGN KEY (return_shipment_id) REFERENCES return_shipments(id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='退货物流轨迹';

-- 21. 平台营销活动
CREATE TABLE IF NOT EXISTS activities (
  id INT AUTO_INCREMENT PRIMARY KEY,
  name VARCHAR(100) NOT NULL COMMENT '活动名称',
  type VARCHAR(20) NOT NULL COMMENT 'FULL满减 / DISCOUNT折扣',
  threshold DECIMAL(10,2) DEFAULT 0 COMMENT '满门槛',
  value DECIMAL(10,2) NOT NULL COMMENT '满减金额或折扣率',
  start_at DATETIME NOT NULL,
  end_at DATETIME NOT NULL,
  status SMALLINT DEFAULT 0 COMMENT '0未开始 1进行中 2已结束',
  description TEXT,
  created_at DATETIME DEFAULT CURRENT_TIMESTAMP
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='平台营销活动';

-- 22. 活动-店铺报名
CREATE TABLE IF NOT EXISTS activity_shops (
  id INT AUTO_INCREMENT PRIMARY KEY,
  activity_id INT NOT NULL,
  shop_id INT NOT NULL,
  joined_at DATETIME DEFAULT CURRENT_TIMESTAMP,
  KEY idx_act_shop (activity_id, shop_id),
  CONSTRAINT fk_act FOREIGN KEY (activity_id) REFERENCES activities(id),
  CONSTRAINT fk_act_shop FOREIGN KEY (shop_id) REFERENCES shops(id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='活动店铺报名';
