from utils.logger import log_info, log_error
from owlready2 import onto_path, get_ontology

def clear_ontology(ontology_path='./ontology/LocationDescription.rdf'):
    """清除本體中的實體與推理結果"""
    try:
        log_info(f"開始清理本體：{ontology_path}")
        onto = get_ontology(ontology_path).load()

        # 清除不再需要的實體
        for ent in list(onto.instances()):
            if should_remove(ent):
                log_info(f"刪除實體: {ent}")
                ent.remove()

        # 清除推理結果
        # (假設你有需要清除推理結果的邏輯)
        clear_inferences(onto)

        onto.save()

        log_info("本體清理完成。")
    except Exception as e:
        log_error(f"清理本體時發生錯誤：{e}")
        raise

def should_remove(entity):
    """檢查是否需要刪除的條件"""
    # 這裡可以自定義條件，舉例：刪除特定類型的實體
    return entity.name.startswith("temp_")  # 假設刪除名稱以 'temp_' 開頭的實體

def clear_inferences(onto):
    """清除推理結果"""
    # 這裡應該有清除推理結果的邏輯
    log_info("清除推理結果...")
    # 假設清除規則與推理狀態
    onto.destroy()