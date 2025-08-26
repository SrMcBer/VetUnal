from typing import List
from .text_classifier import PageInfo, PageType

class PageResolver:
    def __init__(self, pages: List[PageInfo]):
        self.pages = pages

    def is_type(self, i: int, page_type: PageType) -> bool:
        return 0 <= i < len(self.pages) and self.pages[i].page_type == page_type
    
    def is_unknown(self, i: int) -> bool:
        return self.is_type(i, PageType.UNKNOWN)
    
    def apply_rules(self, rules_funcs: List[callable]) -> None:
        i = 0
        while i < len(self.pages):
            for rule in rules_funcs:
                new_index = rule(i)
                if new_index is not None:
                    i = new_index
                    break
            else:
                i += 1
    
    # ? rule functions
    
    # Rule A: HISTORIA - HISTORIA - UNKNOWN - RECIBO
    def rule_a(self, i: int) -> int | None:
        if (i + 4 < len(self.pages) and
            self.is_type(i, PageType.HISTORIA_CLINICA) and
            self.is_type(i + 1, PageType.HISTORIA_CLINICA) and
            self.is_unknown(i + 2) and
            self.is_type(i + 3, PageType.RECIBO)):
            print(f"Applying Rule A at index {i}")
            print(f"Converting page {i + 3} - {self.pages[i + 2].page_type} to CEDULA")
            self.pages[i + 2].page_type = PageType.CEDULA
            return i + 4
        return None

    # Rule B: HISTORIA - HISTORIA - UNKNOWN - UNKNOWN - HISTORIA
    def rule_b(self, i: int) -> int | None:
        if (i + 4 < len(self.pages) and
            self.is_type(i, PageType.HISTORIA_CLINICA) and
            self.is_type(i + 1, PageType.HISTORIA_CLINICA) and
            self.is_unknown(i + 2) and
            self.is_unknown(i + 3) and
            self.is_type(i + 4, PageType.HISTORIA_CLINICA)):
            print(f"Applying Rule B at index {i}")
            print(f"Converting page {i + 3} - {self.pages[i + 2].page_type} to CEDULA")
            print(f"Converting page {i + 4} - {self.pages[i + 3].page_type} to RECIBO")
            self.pages[i + 2].page_type = PageType.CEDULA
            self.pages[i + 3].page_type = PageType.RECIBO
            return i + 4
        return None

    # Rule C: CEDULA - UNKNOWN - HISTORIA (pattern completion)
    def rule_c(self, i: int) -> int | None:
        if (i + 2 < len(self.pages) and
            self.is_type(i, PageType.CEDULA) and
            self.is_unknown(i + 1) and
            self.is_type(i + 2, PageType.HISTORIA_CLINICA)):
            print(f"Applying Rule C at index {i}")
            print(f"Converting page {i + 2} - {self.pages[i + 1].page_type} to RECIBO")
            self.pages[i + 1].page_type = PageType.RECIBO
            return i + 2
        return None
    
    # Rule D: HISTORIA - HISTORIA - UNKNOWN - CEDULA - RECIBO
    def rule_d(self, i: int) -> int | None:
        if(i + 4 < len(self.pages) and
            self.is_type(i, PageType.HISTORIA_CLINICA) and
            self.is_type(i + 1, PageType.HISTORIA_CLINICA) and
            self.is_unknown(i + 2) and
            self.is_type(i + 3, PageType.CEDULA) and
            self.is_type(i + 4, PageType.RECIBO)
            ):
            print(f"Applying Rule D at index {i}")
            print(f"Converting page {i + 3} - {self.pages[i + 2].page_type} to CEDULA")
            print(f"Converting page {i + 4} - {self.pages[i + 3].page_type} to RECIBO")
            self.pages[i + 2].page_type = PageType.CEDULA
            self.pages[i + 3].page_type = PageType.RECIBO
            return i + 4
        return None
    
    # Rule E: HISTORIA - HISTORIA - UNKNOWN - CEDULA (at end or before HISTORIA)
    def rule_e(self, i: int) -> int | None:
        if (i + 3 < len(self.pages) and
            self.is_type(i, PageType.HISTORIA_CLINICA) and
            self.is_type(i + 1, PageType.HISTORIA_CLINICA) and
            self.is_unknown(i + 2) and
            self.is_type(i + 3, PageType.CEDULA) and
            (i + 4 >= len(self.pages) or self.is_type(i + 4, PageType.HISTORIA_CLINICA))):
            print(f"Applying Rule E at index {i}")
            print(f"Converting page {i + 3} - {self.pages[i + 2].page_type} to CEDULA")
            print(f"Converting page {i + 4} - {self.pages[i + 3].page_type} to RECIBO")
            self.pages[i + 2].page_type = PageType.CEDULA
            self.pages[i + 3].page_type = PageType.RECIBO
            return i + 3
        return None
    
    # Rule F: CEDULA - UNKNOWN - RECIBO (multi-page RECIBO)
    def rule_f(self, i: int) -> int | None:
        if (i + 2 < len(self.pages) and
            self.is_type(i, PageType.CEDULA) and
            self.is_unknown(i + 1) and
            self.is_type(i + 2, PageType.RECIBO)):
            print(f"Applying Rule F at index {i}")
            print(f"Converting page {i + 2} - {self.pages[i + 1].page_type} to CEDULA")
            self.pages[i + 1].page_type = PageType.RECIBO
            return i + 2
        return None
    
    # Rule G: RECIBO - UNKNOWN - HISTORIA (multi-page RECIBO)
    def rule_g(self, i: int) -> int | None:
        if (i + 2 < len(self.pages) and
            self.is_type(i, PageType.RECIBO) and
            self.is_unknown(i + 1) and
            self.is_type(i + 2, PageType.HISTORIA_CLINICA)):
            print(f"Applying Rule G at index {i}")
            print(f"Converting page {i + 2} - {self.pages[i + 1].page_type} to RECIBO")
            self.pages[i + 1].page_type = PageType.RECIBO
            return i + 2
        return None
    
    # Rule H: Fix HISTORIA - RECIBO - CEDULA → HISTORIA - CEDULA - RECIBO
    def rule_h(self, i: int) -> int | None:
        if (self.is_type(i - 1, PageType.HISTORIA_CLINICA) and
            self.is_type(i, PageType.RECIBO) and
            self.is_type(i + 1, PageType.CEDULA)):
            print(f"Applying Rule H at index {i - 1}")
            self.pages[i].page_type = PageType.CEDULA
            self.pages[i + 1].page_type = PageType.RECIBO
            return i + 2
        return None
    
    # Rule I: Enforce "only one CEDULA per user" - look for duplicate CEDULAs in same sequence
    def rule_i(self, i: int) -> int | None:
        if (i + 1 < len(self.pages) and
            self.is_type(i, PageType.CEDULA) and
            self.is_type(i + 1, PageType.CEDULA)):
            has_historia_before = False
            for j in range(max(0, i - 3), i):
                if self.is_type(j, PageType.HISTORIA_CLINICA):
                    has_historia_before = True
                    break
            
            if has_historia_before:
                print(f"Applying Rule I at index {i}")
                print(f"Converting page {i + 2} - {self.pages[i + 1].page_type} to RECIBO")
                self.pages[i + 1].page_type = PageType.RECIBO
            return i + 2
        return None
    
    def rule_j(self, i: int) -> int | None:
        if (i + 2 < len(self.pages) and
            self.is_type(i, PageType.CEDULA) and
            self.is_type(i + 1, PageType.RECIBO) and
            self.is_type(i + 2, PageType.CEDULA)):
            has_historia_before = False
            for j in range(max(0, i - 3), i):
                if self.is_type(j, PageType.HISTORIA_CLINICA):
                    has_historia_before = True
                    break
            
            if has_historia_before:
                print(f"Applying Rule J at index {i}")
                print(f"Converting page {i + 3} - {self.pages[i + 2].page_type} to RECIBO")
                self.pages[i + 2].page_type = PageType.RECIBO
            return i + 2
        return None

    def resolve(self) -> List[PageInfo]:
        self.apply_rules([
            self.rule_a,
            self.rule_b,
            self.rule_c,
            self.rule_d,
            self.rule_e,
            self.rule_f,
            self.rule_g
        ])
        
        self.apply_rules([
            self.rule_h,
        ])
        
        self.apply_rules([
            self.rule_i
        ])
        
        self.apply_rules([
            self.rule_j
        ])
        
        return self.pages

def resolve_unknown_page_types(pages: List[PageInfo]) -> List[PageInfo]:
    return PageResolver(pages.copy()).resolve()