import pandas as pd
import numpy as np
import utils as ut

class ItemDataCreator:
    def __init__(self, item_data_path, display_data_path, sales_data_path, shelf_capacity=1000, min_spacing=5, max_spacing=20):
        # item_data_path：商品数据文件路径，即ADS_SPAM_SPACE_ITEM_ATTRIBUTE_WTCCN_V.csv
        # current_display_data_path：当前陈列数据文件路径，可将pog_result.csv用于测试
        # sales_data_path: 销售数据文件路径，即sales_item_sum.csv
        # shelf_capacity: 货架容量
        
        self.item_data_path = pd.read_csv(item_data_path)
        self.display_data_path = pd.read_csv(display_data_path)
        self.sales_data = pd.read_csv(sales_data_path)
        self.shelf_capacity = shelf_capacity
        self.min_spacing = min_spacing
        self.max_spacing = max_spacing
        
        # 模拟商品分组层级数据（实际应用中应从数据库获取）
        self.product_hierarchy = self._generate_hierarchy_data()
        
        # 模拟货架布局数据（实际应用中应从数据库获取）
        self.shelf_layout = self._generate_shelf_layout()
        
        # 固定删除规则SKU列表（实际应用中应从配置获取）
        self.fixed_removal_skus = ['101429421', '101439625']  # 示例SKU
    
    def _generate_hierarchy_data(self):
        """生成模拟的商品分组层级数据"""
        hierarchy = {}
        for item_code in self.sales_data['item_code']:
            # 模拟分组层级：部门->大类->中类->小类
            dept = str(item_code)[:3] + '00'
            category = str(item_code)[:4] + '0'
            sub_category = str(item_code)[:5]
            item_class = str(item_code)
            
            hierarchy[item_code] = {
                'department': dept,
                'category': category,
                'sub_category': sub_category,
                'item_class': item_class,
                'levels': ['department', 'category', 'sub_category', 'item_class']
            }
        return hierarchy
    
    def _generate_shelf_layout(self):
        """生成模拟的货架布局数据"""
        layout = {}
        
        # 模拟多个货架
        for shelf_id in range(1, 6):
            layout[f'shelf_{shelf_id}'] = {}
            
            # 每个货架有3-5层
            for layer_id in range(1, np.random.randint(3, 6)):
                layout[f'shelf_{shelf_id}'][f'layer_{layer_id}'] = {
                    'capacity': self.shelf_capacity,
                    'current_products': [],
                    'current_spacing': self.max_spacing,
                    'used_capacity': 0,
                    'hierarchy_groups': set()
                }
        
        # 随机分配一些商品到货架
        sample_products = self.sales_data['item_code'].sample(min(100, len(self.sales_data))).tolist()
        
        for product in sample_products:
            shelf_id = f'shelf_{np.random.randint(1, 6)}'
            layer_id = f'layer_{np.random.randint(1, len(layout[shelf_id]) + 1)}'
            
            product_size = np.random.randint(10, 50)  # 模拟商品尺寸
            facing = 1  # 初始排面数
            
            layout[shelf_id][layer_id]['current_products'].append({
                'item_code': product,
                'size': product_size,
                'facing': facing,
                'sales': self.sales_data[self.sales_data['item_code'] == product]['sales'].values[0]
            })
            
            layout[shelf_id][layer_id]['used_capacity'] += product_size * facing
            layout[shelf_id][layer_id]['hierarchy_groups'].add(
                self.product_hierarchy[product]['department']
            )
        
        return layout
    
    def find_display_position(self, new_product_code):
        """
        为新商品寻找陈列位置
        
        参数:
        - new_product_code: 新商品编码
        
        返回:
        - 目标货架和层信息
        """
        if new_product_code not in self.product_hierarchy:
            raise ValueError(f"商品 {new_product_code} 未找到分组信息")
        
        new_product_hierarchy = self.product_hierarchy[new_product_code]
        
        # 从最小层级开始向上寻找匹配的陈列位置
        for level in reversed(new_product_hierarchy['levels']):
            target_group = new_product_hierarchy[level]
            
            print(f"在层级 {level} 寻找分组 {target_group} 的陈列位置...")
            
            for shelf_id, shelf_data in self.shelf_layout.items():
                for layer_id, layer_data in shelf_data.items():
                    # 检查该层是否有相同分组的商品
                    if any(target_group in str(group) for group in layer_data['hierarchy_groups']):
                        print(f"找到匹配位置: {shelf_id} - {layer_id}")
                        return {
                            'shelf_id': shelf_id,
                            'layer_id': layer_id,
                            'layer_data': layer_data,
                            'matched_level': level
                        }
        
        # 如果所有层级都没找到，使用第一个可用的位置
        for shelf_id, shelf_data in self.shelf_layout.items():
            for layer_id, layer_data in shelf_data.items():
                if layer_data['used_capacity'] < layer_data['capacity']:
                    print(f"未找到匹配分组，使用可用位置: {shelf_id} - {layer_id}")
                    return {
                        'shelf_id': shelf_id,
                        'layer_id': layer_id,
                        'layer_data': layer_data,
                        'matched_level': 'any'
                    }
        
        raise Exception("没有可用的陈列位置")
    
    def calculate_required_space(self, new_product_size, facing=1):
        """计算商品所需空间"""
        return new_product_size * facing + self.min_spacing
    
    def adjust_spacing(self, layer_data, new_product_size):
        """
        调整商品间距以容纳新商品
        
        参数:
        - layer_data: 层数据
        - new_product_size: 新商品尺寸
        
        返回:
        - 是否调整成功
        - 调整后的层数据
        """
        required_space = self.calculate_required_space(new_product_size)
        available_space = layer_data['capacity'] - layer_data['used_capacity']
        
        print(f"所需空间: {required_space}, 可用空间: {available_space}")
        
        # 如果当前可用空间足够
        if available_space >= required_space:
            return True, layer_data
        
        # 尝试调整间距
        current_spacing = layer_data['current_spacing']
        product_count = len(layer_data['current_products'])
        
        for new_spacing in range(current_spacing - 1, self.min_spacing - 1, -1):
            spacing_saved = (current_spacing - new_spacing) * product_count
            new_available_space = available_space + spacing_saved
            
            print(f"调整间距从 {current_spacing} 到 {new_spacing}, 节省空间: {spacing_saved}")
            
            if new_available_space >= required_space:
                layer_data['current_spacing'] = new_spacing
                layer_data['used_capacity'] -= spacing_saved
                return True, layer_data
        
        return False, layer_data
    
    def find_double_facing_products(self, layer_data):
        """找出有double facing的商品并按销售额排序"""
        double_facing_products = [
            p for p in layer_data['current_products'] 
            if p['facing'] > 1
        ]
        
        # 按销售额从低到高排序
        return sorted(double_facing_products, key=lambda x: x['sales'])
    
    def remove_low_sales_double_facing(self, layer_data, required_space):
        """
        移除销售额低的double facing商品
        
        参数:
        - layer_data: 层数据
        - required_space: 所需空间
        
        返回:
        - 是否移除成功
        - 更新后的层数据
        """
        double_facing_products = self.find_double_facing_products(layer_data)
        
        for product in double_facing_products:
            # 减少一个排面
            space_freed = product['size']
            product['facing'] -= 1
            
            layer_data['used_capacity'] -= space_freed
            available_space = layer_data['capacity'] - layer_data['used_capacity']
            
            print(f"减少商品 {product['item_code']} 的排面，释放空间: {space_freed}")
            
            if available_space >= required_space:
                return True, layer_data
        
        return False, layer_data
    
    def remove_fixed_skus(self, layer_data, required_space):
        """
        按照固定规则删除SKU
        
        参数:
        - layer_data: 层数据
        - required_space: 所需空间
        
        返回:
        - 是否删除成功
        - 更新后的层数据
        """
        removable_products = [
            p for p in layer_data['current_products'] 
            if str(p['item_code']) in self.fixed_removal_skus
        ]
        
        # 按销售额从低到高排序
        removable_products.sort(key=lambda x: x['sales'])
        
        for product in removable_products:
            space_freed = product['size'] * product['facing'] + self.min_spacing
            layer_data['current_products'].remove(product)
            layer_data['used_capacity'] -= space_freed
            layer_data['hierarchy_groups'] = set(
                self.product_hierarchy[p['item_code']]['department'] 
                for p in layer_data['current_products']
            )
            
            available_space = layer_data['capacity'] - layer_data['used_capacity']
            
            print(f"删除商品 {product['item_code']}，释放空间: {space_freed}")
            
            if available_space >= required_space:
                return True, layer_data
        
        return False, layer_data
    
    def add_new_product(self, new_product_code, new_product_size=30):
        """
        添加新商品到陈列
        
        参数:
        - new_product_code: 新商品编码
        - new_product_size: 新商品尺寸（默认为30）
        
        返回:
        - 操作结果
        """
        print(f"开始处理新商品 {new_product_code} 的陈列...")
        
        try:
            # 1. 寻找陈列位置
            position_info = self.find_display_position(new_product_code)
            shelf_id = position_info['shelf_id']
            layer_id = position_info['layer_id']
            layer_data = position_info['layer_data']
            
            print(f"确定陈列位置: {shelf_id} - {layer_id}")
            
            # 2. 计算所需空间
            required_space = self.calculate_required_space(new_product_size)
            print(f"新商品所需空间: {required_space}")
            
            # 3. 尝试调整间距
            success, updated_layer_data = self.adjust_spacing(layer_data, new_product_size)
            
            if success:
                print("通过调整间距成功获得空间")
                layer_data = updated_layer_data
            else:
                print("调整间距后空间仍不足，尝试处理double facing商品...")
                
                # 4. 尝试移除double facing商品
                success, updated_layer_data = self.remove_low_sales_double_facing(
                    layer_data, required_space
                )
                
                if success:
                    print("通过减少double facing商品排面成功获得空间")
                    layer_data = updated_layer_data
                else:
                    print("无double facing商品或空间仍不足，尝试删除固定SKU...")
                    
                    # 5. 尝试删除固定SKU
                    success, updated_layer_data = self.remove_fixed_skus(
                        layer_data, required_space
                    )
                    
                    if success:
                        print("通过删除固定SKU成功获得空间")
                        layer_data = updated_layer_data
                    else:
                        raise Exception("陈列空间不足，无法安置新商品")
            
            # 添加新商品
            new_product_sales = self.sales_data[
                self.sales_data['item_code'] == new_product_code
            ]['sales'].values[0] if new_product_code in self.sales_data['item_code'].values else 0
            
            layer_data['current_products'].append({
                'item_code': new_product_code,
                'size': new_product_size,
                'facing': 1,
                'sales': new_product_sales
            })
            
            layer_data['used_capacity'] += required_space
            layer_data['hierarchy_groups'].add(
                self.product_hierarchy[new_product_code]['department']
            )
            
            # 更新货架布局
            self.shelf_layout[shelf_id][layer_id] = layer_data
            
            result = {
                'success': True,
                'message': f"成功将商品 {new_product_code} 陈列在 {shelf_id} - {layer_id}",
                'position': {
                    'shelf': shelf_id,
                    'layer': layer_id,
                    'matched_level': position_info['matched_level']
                },
                'remaining_capacity': layer_data['capacity'] - layer_data['used_capacity']
            }
            
            print(result['message'])
            return result
            
        except Exception as e:
            error_msg = f"添加商品 {new_product_code} 失败: {str(e)}"
            print(error_msg)
            return {
                'success': False,
                'message': error_msg
            }
    
    def get_shelf_status(self, shelf_id=None):
        """获取货架状态"""
        if shelf_id:
            return self.shelf_layout.get(shelf_id, {})
        else:
            return self.shelf_layout
    
    def get_product_info(self, product_code):
        """获取商品信息"""
        if product_code in self.product_hierarchy:
            sales_info = self.sales_data[
                self.sales_data['item_code'] == product_code
            ]
            return {
                'hierarchy': self.product_hierarchy[product_code],
                'sales': sales_info['sales'].values[0] if not sales_info.empty else 0,
                'qty': sales_info['qty'].values[0] if not sales_info.empty else 0
            }
        return None

# 使用示例
def main():
    # 初始化优化器
    optimizer = ItemDataCreator('ADS_SPAM_SPACE_ITEM_ATTRIBUTE_WTCCN_V.csv','pog_result.csv','sales_item_sum.csv')
    
    # 示例1：添加新商品
    new_product = '101450423'  # 从数据中选择一个商品作为示例
    result = optimizer.add_new_product(new_product, new_product_size=35)
    print(f"结果: {result}")
    
    # 示例2：查看货架状态
    # shelf_status = optimizer.get_shelf_status('shelf_1')
    # print(f"货架1状态: {shelf_status}")
    
    # 示例3：获取商品信息
    product_info = optimizer.get_product_info(new_product)
    print(f"商品信息: {product_info}")

if __name__ == "__main__":
    main()