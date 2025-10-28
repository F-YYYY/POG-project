import pandas as pd
from typing import Dict, Optional, List, Tuple


class RemoveSKU:
    """
    RemoveSKU 类
    ------------------
    从POG中删除指定SKU，并禁止删除托盘(tray)或托盘上的商品。
    """

    def __init__(self):
        self.dataframes: Dict[str, pd.DataFrame] = {}
        self.affected_layers_by_removal: List[Tuple[int, int]] = []
        print("✅ RemoveSKU 初始化完成。")

    def remove_sku_items(self, var_dict: Dict):
        pog_data = var_dict['bases_data']['pog_data']
        params = var_dict['func'].get('del_item_func', {})
        delete_skus = params.get('del_item_list', [])

        print(f"\n--- 开始执行 'remove_sku_items' 删除SKU: {delete_skus} ---")

        if pog_data is None or pog_data.empty:
            return pog_data, {'status': 'fail', 'msg': 'POG数据为空'}

        if 'item_code' not in pog_data.columns:
            return pog_data, {'status': 'fail', 'msg': "缺少字段 'item_code'"}

        # ==== 检查是否存在 tray 或 tray 上商品 ====
        if 'item_type' in pog_data.columns:
            tray_items = pog_data.loc[pog_data['item_type'] == 'tray', 'item_code'].astype(str).tolist()

            # 禁止直接删除托盘
            for code in delete_skus:
                if str(code) in tray_items:
                    return pog_data, {
                        'status': 'fail',
                        'msg': f'删除失败：SKU {code} 是托盘(tray)商品，禁止删除。'
                    }

            # 禁止删除托盘上的商品
            if 'tray_id' in pog_data.columns and pog_data['tray_id'].notna().any():
                trays = pog_data.loc[pog_data['item_type'] == 'tray', 'tray_id'].dropna().unique()
                linked_items = pog_data[
                    (pog_data['item_type'] == 'item') &
                    (pog_data['tray_id'].isin(trays))
                ]
                linked_skus = linked_items['item_code'].astype(str).tolist()

                for code in delete_skus:
                    if str(code) in linked_skus:
                        tray_id = linked_items.loc[
                            linked_items['item_code'].astype(str) == str(code), 'tray_id'
                        ].iloc[0]
                        return pog_data, {
                            'status': 'fail',
                            'msg': f'删除失败：SKU {code} 位于托盘 {tray_id} 上，禁止删除。'
                        }

        # ==== 记录受影响层 ====
        affected_layers = pog_data[pog_data['item_code'].isin(delete_skus)][['module_id', 'layer_id']].drop_duplicates()
        self.affected_layers_by_removal = [tuple(x) for x in affected_layers.to_numpy()]

        # ==== 执行删除 ====
        new_pog = pog_data[~pog_data['item_code'].isin(delete_skus)].copy()
        removed_num = len(pog_data) - len(new_pog)
        print(f"🗑️ 已删除 {removed_num} 条SKU记录。")

        return new_pog, {'status': 'success', 'msg': f'成功删除 {removed_num} 个SKU'}

class FillLayerSKU(RemoveSKU):
    """
    FillLayerSKU 类
    ------------------
    删除SKU后：
    1. 检测tray
    2. 计算剩余空间
    3. 仅选一个sales最高且能放得下的商品进行double-facing
    4. 否则直接等距重排（含两端空隙）
    """

    def __init__(self):
        super().__init__()
        self.affected_layer_space: Optional[pd.DataFrame] = None
        self.sorted_items_by_position: Dict[Tuple[int, int], pd.DataFrame] = {}
        print("✅ FillLayerSKU 初始化完成。")

    def analyze_layer_space(self, pog_data: pd.DataFrame, total_layer_width: int = 1000) -> pd.DataFrame:
        """
        分析每层已用空间与剩余空间
        """
        if pog_data.empty:
            return pd.DataFrame(columns=['module_id', 'layer_id', 'item_count', 'used_width', 'remaining_width'])

        layer_summary = pog_data.groupby(['module_id', 'layer_id']).agg(
            used_width=('item_width', 'sum'),
            item_count=('item_code', 'count')
        ).reset_index()
        layer_summary['total_width'] = total_layer_width
        layer_summary['remaining_width'] = layer_summary['total_width'] - layer_summary['used_width']
        return layer_summary

    def calculate_space_for_affected_layers(self, pog_data: pd.DataFrame, total_layer_width: int = 1000):
        """
        仅计算受影响层的剩余空间
        """
        print("\n--- 计算受影响层剩余空间 ---")
        if not self.affected_layers_by_removal:
            print("ℹ️ 无受影响层。")
            return

        all_layers = self.analyze_layer_space(pog_data, total_layer_width)
        affected = all_layers.set_index(['module_id', 'layer_id']).reindex(self.affected_layers_by_removal)
        self.affected_layer_space = affected.reset_index()
        print("✅ 受影响层空间计算完成。")

    def sort_items_by_position(self, pog_data: pd.DataFrame):
        """
        为受影响层内商品按position排序
        """
        print("\n--- 排序受影响层内商品 ---")
        for mod_id, lay_id in self.affected_layers_by_removal:
            df = pog_data[(pog_data['module_id'] == mod_id) & (pog_data['layer_id'] == lay_id)].copy()
            if df.empty:
                continue
            sorted_df = df.sort_values(by='position')
            self.sorted_items_by_position[(mod_id, lay_id)] = sorted_df
        print("✅ 排序完成。")

    def fill_and_reposition_layers(self, pog_data: pd.DataFrame, total_layer_width: int = 1000):
        """
        自动执行：
        1. 仅选一个销售最高的商品进行双陈列（若能放下）
        2. 否则直接重排
        3. 重排采用“两端留空”的等距分布
        """
        print("\n--- 开始执行填充与重新定位 ---")
        updated_layers = []

        for layer_key, layer_df in self.sorted_items_by_position.items():
            mod_id, lay_id = layer_key

            layer_space = self.analyze_layer_space(pog_data)
            remain = layer_space[
                (layer_space['module_id'] == mod_id) &
                (layer_space['layer_id'] == lay_id)
            ]['remaining_width'].iloc[0]

            current_remain = remain
            copies_to_add = {}

            # ✅ step1: 仅尝试一个sales最高且能放下的商品进行双陈列
            if 'sales' in layer_df.columns:
                sorted_by_sales = layer_df.sort_values(by='sales', ascending=False)
            else:
                sorted_by_sales = layer_df  # 若无sales字段，则不排序

            for _, row in sorted_by_sales.iterrows():
                width = row['item_width']
                code = row['item_code']
                if current_remain >= width:
                    copies_to_add[code] = 1
                    current_remain -= width
                    print(f"➕ 本层 {mod_id}-{lay_id} 增加双陈列商品: {code}")
                    break  # 仅一个商品
            else:
                print(f"ℹ️ 本层 {mod_id}-{lay_id} 未增加任何商品。")

            # ✅ step2: 构建新层数据
            new_items = []
            for _, row in layer_df.iterrows():
                new_items.append(row.to_dict())
                if row['item_code'] in copies_to_add:
                    copy = row.to_dict()
                    copy['position'] = -1
                    new_items.append(copy)

            # ✅ step3: 等距重排（含两端空隙）
            total_width = sum(i['item_width'] for i in new_items)
            spacing = (total_layer_width - total_width) / (len(new_items) + 1)
            pos = spacing
            for item in new_items:
                item['position'] = pos
                pos += item['item_width'] + spacing

            updated_layers.append(pd.DataFrame(new_items))

        if not updated_layers:
            return pog_data, {'status': 'success', 'msg': '无可更新层'}

        # ✅ 合并结果
        new_layers = pd.concat(updated_layers, ignore_index=True)
        unaffected = pog_data.set_index(['module_id', 'layer_id']).drop(
            index=pd.MultiIndex.from_tuples(self.affected_layers_by_removal, names=['module_id', 'layer_id']),
            errors='ignore'
        ).reset_index()
        new_pog = pd.concat([unaffected, new_layers], ignore_index=True)

        print("✅ 填充与重新定位完成。")
        return new_pog, {'status': 'success', 'msg': '填充与重新定位成功'}

    def run_delete_fill_pipeline(self, var_dict: Dict) -> Tuple[pd.DataFrame, Dict]:
        """
        一键执行完整删除+重排流程
        """
        pog_data, status = self.remove_sku_items(var_dict)
        if status['status'] == 'fail':
            return pog_data, status

        self.calculate_space_for_affected_layers(pog_data)
        self.sort_items_by_position(pog_data)
        new_pog, status2 = self.fill_and_reposition_layers(pog_data)

        return new_pog, status2


# ===========================
# ✅ 示例调用
# ===========================
if __name__ == "__main__":
    var_dict = {
        'bases_data': {
            'pog_data': pd.read_csv("pog_result.csv")
        },
        'func': {
            'del_item_func': {
                'del_item_list': ['6', '100020974']
            }
        }
    }

    filler = FillLayerSKU()
    new_pog, status = filler.run_delete_fill_pipeline(var_dict)

    print(status)
    new_pog.to_csv("pog_result_final_output.csv", index=False, encoding='utf-8-sig')
    print("✅ 最终结果已导出。")
