import pandas as pd
import numpy as np

def add_item_func(var_dict):
    """
    新增一个品，旧品不动 - 场景函数
    
    参数:
    var_dict: 包含基础数据和函数参数的字典
    
    返回:
    dict: 包含新pog_data和状态信息的字典
    """
    try:
        # 从var_dict中获取基础数据
        bases_data = var_dict['bases_data']
        pog_data = bases_data['pog_data'].copy()
        tray_item = bases_data['tray_item']
        item_attributes = bases_data['item_attributes']
        sales_data = bases_data['sales_data']
        brand_hierarchy = bases_data['brand_hierarchy']
        
        # 从var_dict中获取即将添加的商品编号
        add_item = var_dict['add_item']
        
        # Step1：检查是否为托盘商品
        if check_tray_item(add_item, tray_item):
            return {
                'pog_data': pog_data,
                'status': 'fail',
                'error_msg': f'新增的商品 {add_item} 是托盘商品，不能在商品区域陈列'
            }
        
        # Step2：定位商品位置
        position_result = locate_item_position(add_item, pog_data, item_attributes, brand_hierarchy, sales_data)
        if not position_result['success']:
            return {
                'pog_data': pog_data,
                'status': 'fail',
                'error_msg': position_result['error_msg']
            }
        
        target_module = position_result['module']
        target_layer = position_result['layer']
        item_width = position_result['item_width']
        
        # Step3：尝试在目标层插入商品
        insert_result = insert_item_to_target_layer(
            pog_data, add_item, item_width, target_module, target_layer, sales_data
        )
        
        if insert_result['success']:
            return {
                'pog_data': insert_result['new_pog_data'],
                'status': 'success',
                'error_msg': '',
                'target_module': target_module,
                'target_layer': target_layer
            }
        else:
            return {
                'pog_data': pog_data,
                'status': 'fail',
                'error_msg': insert_result['error_msg']
            }
            
    except Exception as e:
        return {
            'pog_data': pog_data,
            'status': 'fail',
            'error_msg': f'函数执行出错: {str(e)}'
        }

def check_tray_item(item_code, tray_config):
    """检查商品是否为托盘商品且不能在商品区域陈列"""
    # 简化实现，暂时返回False
    # TODO：补全这里
    return False

def locate_item_position(item_code, pog_data, item_attributes, brand_hierarchy, sales_data):
    """
    定位商品应该放在哪个模块和层
    按照品牌层级结构从细到粗查找
    """
    # 获取商品属性
    item_info = get_item_info(item_code, item_attributes, brand_hierarchy)
    if item_info is None:
        return {
            'success': False,
            'error_msg': f'未找到商品 {item_code} 的属性信息'
        }
    
    item_width = get_item_width(item_code, item_attributes)
    if item_width is None:
        return {
            'success': False,
            'error_msg': f'未找到商品 {item_code} 的宽度信息'
        }
    
    # 获取商品的品牌层级信息
    brand = item_info.get('brand')
    series = item_info.get('series')
    category = item_info.get('category')
    brand_label = item_info.get('brand_label')
    
    # 按照层级从细到粗查找匹配位置
    hierarchy_levels = [
        {'brand': brand, 'series': series, 'category': category},  # 最细粒度
        {'brand': brand, 'series': series},  # 品牌+系列
        {'brand': brand},  # 仅品牌
        {'brand_label': brand_label}  # 品牌集合
    ]
    
    for level in hierarchy_levels:
        position = find_matching_position(level, pog_data, item_attributes, brand_hierarchy)
        if position is not None:
            return {
                'success': True,
                'module': position['module'],
                'layer': position['layer'],
                'item_width': item_width
            }
    
    # 如果所有层级都找不到匹配
    return {
        'success': False,
        'error_msg': f'无法为商品 {item_code} 找到合适的摆放位置'
    }

def get_item_info(item_code, item_attributes, brand_hierarchy):
    """获取商品的完整属性信息"""
    # 从商品属性表获取基本信息
    item_row = item_attributes[item_attributes['ITEM_NBR'] == int(item_code)]
    if item_row.empty:
        return None
    
    item_info = {
        'item_code': item_code,
        'series': item_row.iloc[0]['SERIES'],
        'item_name': item_row.iloc[0]['ITEM_NAME']
    }
    
    # 从品牌层级表获取品牌信息（这里需要根据实际业务逻辑匹配）
    # 简化实现：假设可以通过系列或其他方式匹配到品牌
    brand_match = brand_hierarchy[brand_hierarchy['brand'].str.contains(item_info['series'], na=False)]
    if not brand_match.empty:
        item_info['brand'] = brand_match.iloc[0]['brand']
        item_info['brand_label'] = brand_match.iloc[0]['brand_label']
    
    return item_info

def get_item_width(item_code, item_attributes):
    """获取商品宽度"""
    # 这里需要根据实际情况获取商品宽度
    # 简化实现：返回默认值80
    return 80

def find_matching_position(level_criteria, pog_data, item_attributes, brand_hierarchy):
    """根据层级条件查找匹配的位置"""
    # 获取满足层级条件的所有商品
    matching_items = get_items_by_hierarchy(level_criteria, pog_data, item_attributes, brand_hierarchy)
    
    if matching_items.empty:
        return None
    
    # 计算每层的剩余空间
    layer_space = calculate_layer_space(matching_items, pog_data)
    if not layer_space:
        return None
    
    # 返回剩余空间最大的层
    max_space_layer = max(layer_space, key=lambda x: x['remaining_space'])
    return {
        'module': max_space_layer['module_id'],
        'layer': max_space_layer['layer_id']
    }

def get_items_by_hierarchy(level_criteria, pog_data, item_attributes, brand_hierarchy):
    """根据层级条件获取匹配的商品"""
    # TODO：这里需要实现根据品牌层级条件筛选商品的逻辑
    # 简化实现：返回所有商品进行测试
    return pog_data[pog_data['item_type'] == 'item']

def calculate_layer_space(matching_items, pog_data):
    """计算匹配商品所在各层的剩余空间"""
    layer_space = []
    
    # 获取匹配商品所在的所有模块和层组合
    layer_groups = matching_items.groupby(['module_id', 'layer_id'])
    
    for (module_id, layer_id), group in layer_groups:
        # 获取该层的所有商品
        layer_items = pog_data[
            (pog_data['module_id'] == module_id) & 
            (pog_data['layer_id'] == layer_id)
        ]
        
        if layer_items.empty:
            continue
            
        module_width = layer_items['module_width'].iloc[0]
        used_space = layer_items['item_width'].sum()
        remaining_space = module_width - used_space
        
        layer_space.append({
            'module_id': module_id,
            'layer_id': layer_id,
            'remaining_space': remaining_space,
            'item_count': len(layer_items)
        })
    
    return layer_space

def insert_item_to_target_layer(pog_data, item_code, item_width, target_module, target_layer, sales_data):
    """在目标层插入商品"""
    new_pog_data = pog_data.copy()
    
    # 获取目标层的所有商品
    layer_mask = (new_pog_data['module_id'] == target_module) & (new_pog_data['layer_id'] == target_layer)
    layer_items = new_pog_data[layer_mask]
    
    if layer_items.empty:
        # 如果该层没有商品，直接添加
        result = add_item_to_empty_layer(new_pog_data, item_code, item_width, target_module, target_layer)
        if result['success']:
            return {'success': True, 'new_pog_data': result['new_pog_data']}
        else:
            return {'success': False, 'error_msg': result['error_msg']}
    
    # 计算当前剩余空间
    module_width = layer_items['module_width'].iloc[0]
    current_used_space = layer_items['item_width'].sum()
    current_remaining_space = module_width - current_used_space
    
    if current_remaining_space >= item_width:
        # 空间足够，直接插入并重排
        result = insert_and_rearrange(new_pog_data, item_code, item_width, target_module, target_layer)
        if result['success']:
            return {'success': True, 'new_pog_data': result['new_pog_data']}
        else:
            return {'success': False, 'error_msg': result['error_msg']}
    else:
        # 空间不足，尝试调整策略
        return adjust_space_for_insertion(new_pog_data, item_code, item_width, target_module, target_layer, sales_data)

def add_item_to_empty_layer(pog_data, item_code, item_width, target_module, target_layer):
    """向空层添加商品"""
    new_pog_data = pog_data.copy()
    
    # 获取模块宽度
    module_info = new_pog_data[new_pog_data['module_id'] == target_module].iloc[0]
    module_width = module_info['module_width']
    
    # 创建新商品行
    new_row = create_new_item_row(new_pog_data, item_code, item_width, target_module, target_layer, 0)
    new_pog_data = pd.concat([new_pog_data, pd.DataFrame([new_row])], ignore_index=True)
    
    return {'success': True, 'new_pog_data': new_pog_data}

def insert_and_rearrange(pog_data, item_code, item_width, target_module, target_layer):
    """插入商品并重排位置"""
    new_pog_data = pog_data.copy()
    
    # 在末尾添加商品
    layer_mask = (new_pog_data['module_id'] == target_module) & (new_pog_data['layer_id'] == target_layer)
    layer_items = new_pog_data[layer_mask]
    
    if layer_items.empty:
        return add_item_to_empty_layer(new_pog_data, item_code, item_width, target_module, target_layer)
    
    # 创建新商品行（临时位置）
    new_row = create_new_item_row(new_pog_data, item_code, item_width, target_module, target_layer, 0)
    new_pog_data = pd.concat([new_pog_data, pd.DataFrame([new_row])], ignore_index=True)
    
    # 重排该层所有商品
    new_pog_data = rearrange_layer_items(new_pog_data, target_module, target_layer)
    
    return {'success': True, 'new_pog_data': new_pog_data}

def create_new_item_row(pog_data, item_code, item_width, target_module, target_layer, position):
    """创建新商品的数据行"""
    # 获取参考行用于填充其他字段
    ref_row = pog_data.iloc[0].copy()
    
    # 构建新行
    new_row = {
        'req_id': pog_data['req_id'].max() + 1,
        'picture_id': ref_row['picture_id'],
        'item_code': item_code,
        'module_id': target_module,
        'module': chr(64 + target_module),  # 1->A, 2->B, ...
        'layer_id': target_layer,
        'position': position,
        'item_width': item_width,
        'facing': 1,
        'item_type': 'item',
        'vert_facing': 1,
        'module_width': ref_row['module_width']
    }
    
    return new_row

def rearrange_layer_items(pog_data, target_module, target_layer):
    """重排指定层的商品位置，平均间隔"""
    new_pog_data = pog_data.copy()
    
    layer_mask = (new_pog_data['module_id'] == target_module) & (new_pog_data['layer_id'] == target_layer)
    layer_indices = new_pog_data[layer_mask].index
    
    if len(layer_indices) == 0:
        return new_pog_data
    
    module_width = new_pog_data.loc[layer_indices[0], 'module_width']
    total_item_width = new_pog_data.loc[layer_indices, 'item_width'].sum()
    
    # 计算平均间隔
    total_gap = module_width - total_item_width
    gap_between_items = total_gap / (len(layer_indices) + 1) if len(layer_indices) > 0 else 0
    
    # 重新分配位置
    current_position = gap_between_items
    for idx in layer_indices:
        new_pog_data.loc[idx, 'position'] = current_position
        current_position += new_pog_data.loc[idx, 'item_width'] + gap_between_items
    
    return new_pog_data

def adjust_space_for_insertion(pog_data, item_code, item_width, target_module, target_layer, sales_data):
    """调整空间策略：减少facing或删除商品"""
    new_pog_data = pog_data.copy()
    layer_mask = (new_pog_data['module_id'] == target_module) & (new_pog_data['layer_id'] == target_layer)
    
    # 策略1: 尝试减少double facing商品的facing
    double_facing_items = new_pog_data[layer_mask & (new_pog_data['facing'] > 1)]
    
    if not double_facing_items.empty:
        # 获取销售数据并排序（从低到高）
        sorted_items = get_sorted_items_by_sales(double_facing_items, sales_data, ascending=True)
        
        for idx in sorted_items.index:
            # 减少一个facing
            original_facing = new_pog_data.loc[idx, 'facing']
            new_pog_data.loc[idx, 'facing'] = original_facing - 1
            
            # 检查空间是否足够
            layer_items_after_adjust = new_pog_data[layer_mask]
            module_width = layer_items_after_adjust['module_width'].iloc[0]
            used_space_after = layer_items_after_adjust['item_width'].sum()
            remaining_space_after = module_width - used_space_after
            
            if remaining_space_after >= item_width:
                # 空间足够，插入商品
                result = insert_and_rearrange(new_pog_data, item_code, item_width, target_module, target_layer)
                if result['success']:
                    return {'success': True, 'new_pog_data': result['new_pog_data']}
            
            # 如果还是不够，恢复原状继续尝试下一个
            new_pog_data.loc[idx, 'facing'] = original_facing
    
    # 策略2: 删除销售最低的商品
    layer_items = new_pog_data[layer_mask]
    if len(layer_items) > 1:
        # 获取销售数据并排序（从低到高）
        sorted_items = get_sorted_items_by_sales(layer_items, sales_data, ascending=True)
        
        for idx in sorted_items.index:
            # 删除一个商品
            temp_pog_data = new_pog_data.drop(index=idx)
            
            # 检查空间是否足够
            temp_layer_items = temp_pog_data[
                (temp_pog_data['module_id'] == target_module) & 
                (temp_pog_data['layer_id'] == target_layer)
            ]
            module_width = temp_layer_items['module_width'].iloc[0]
            used_space_after = temp_layer_items['item_width'].sum()
            remaining_space_after = module_width - used_space_after
            
            if remaining_space_after >= item_width:
                # 空间足够，插入商品
                result = insert_and_rearrange(temp_pog_data, item_code, item_width, target_module, target_layer)
                if result['success']:
                    return {'success': True, 'new_pog_data': result['new_pog_data']}
    
    # 所有策略都失败
    return {
        'success': False, 
        'error_msg': f'空间不足，无法添加商品 {item_code}，即使调整facing和删除商品后仍然无法容纳'
    }

def get_sorted_items_by_sales(items_df, sales_data, ascending=True):
    """根据销售数据对商品进行排序"""
    # 合并销售数据
    merged_df = items_df.merge(
        sales_data, 
        left_on='item_code', 
        right_on='item_code', 
        how='left'
    )
    
    # 填充缺失的销售数据
    merged_df['sales'] = merged_df['sales'].fillna(0)
    
    # 按销售排序
    return merged_df.sort_values('sales', ascending=ascending)

# 使用示例
if __name__ == "__main__":
    # 数据加载
    pog_data = pd.read_csv('pog_result.csv')
    tray_item = pd.read_csv('pog_test_haircare_tray.csv')
    item_attributes = pd.read_csv('pog_test_haircare_test.csv')
    brand_hierarchy = pd.read_csv('brand_2_brand_label.csv')
    sales_data = pd.read_csv('sales_item_sum.csv')
    
    # 构建var_dict
    var_dict = {
        'bases_data': {
            'pog_data': pog_data,
            'tray_item': tray_item,
            'item_attributes': item_attributes,
            'brand_hierarchy': brand_hierarchy,
            'sales_data': sales_data
        },
        'add_item': 101437322  # 示例商品编码，位于pog_test_haircare_test.csv的首行
    }
    
    # 执行函数
    result = add_item_func(var_dict)
    
    print(f"执行状态: {result['status']}")
    if result['status'] == 'success':
        result['pog_data'].to_csv('add_pog_result.csv', index=False)
        print("商品添加成功！")
        print(f"新pog_data形状: {result['pog_data'].shape}")
    else:
        print(f"错误信息: {result['error_msg']}")