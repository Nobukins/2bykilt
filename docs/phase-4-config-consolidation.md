# Phase 4: Issue #355 - Config Consolidation Implementation

**Date**: 2025-10-21  
**Issue**: #355  
**Target**: Configuration & Artifact Management Code Reduction  
**Goal**: 30-40% reduction in config/artifact module lines

## Quick Analysis

### Current Code Inventory

| Module | Lines | Status |
|--------|-------|--------|
| `src/config/feature_flags.py` | 657 | Core config resolution |
| `src/config/multi_env_loader.py` | 625 | Environment-based loading |
| `src/core/artifact_manager.py` | 549 | Artifact persistence |
| Config utilities (parsers, validators) | ~1000 | Supporting modules |
| **Total** | **~2827** | |

### Identified Overlaps

1. **Feature Flags + Multi Env Loader** (1282 lines)
   - Both implement YAML loading
   - Both have precedence resolution (runtime > env > file)
   - Both write artifacts lazily
   - Both use threading locks
   - **Potential consolidation**: 30-40% reduction

2. **Config Parsers** (352 lines)
   - `llms_parser.py` + `llms_schema_validator.py`
   - Duplicated validation logic
   - **Potential consolidation**: 25-30% reduction

3. **Artifact Manager** (549 lines)
   - Overlaps with config artifact generation
   - Recording path logic can be simplified (post #353)
   - **Potential consolidation**: 15-20% reduction

## Proposed Strategy

### Phase 4A: Create Shared Foundation (45 min)

**New module**: `src/config/_core/__init__.py`

1. **Unified Config Resolver**
   - `ConfigSource` abstraction (file, env, override)
   - `ChainResolver` for precedence
   - Shared YAML loading, env var resolution
   - **Lines**: ~120

2. **Unified Artifact Writer**
   - `ArtifactWriter` class
   - Shared masking logic
   - Metadata generation
   - **Lines**: ~100

3. **Shared Validation**
   - `ConfigParser[T]` generic class
   - Type coercion utilities
   - Error formatting
   - **Lines**: ~80

### Phase 4B: Refactor FeatureFlags (30 min)

**Changes**:

- Use `ChainResolver` instead of manual precedence
- Use `ArtifactWriter` for lazy artifacts
- Remove duplicate YAML parsing
- Consolidate locking strategy

**Result**: 657 → ~420 lines (-237 lines, -36%)

### Phase 4C: Refactor MultiEnvLoader (30 min)

**Changes**:

- Use `ChainResolver` for env hierarchy
- Use `ArtifactWriter` for effective config
- Consolidate diff utilities
- Shared error handling

**Result**: 625 → ~420 lines (-205 lines, -33%)

### Phase 4D: Consolidate Parsers (30 min)

**Changes**:

- Merge `llms_parser.py` + `llms_schema_validator.py`
- Use generic `ConfigParser[T]` base
- Embedded validation

**Result**: 352 → 250 lines (-102 lines, -29%)

### Phase 4E: Simplify Artifact Manager (20 min)

**Changes**:

- Use `ArtifactWriter` for all persistence
- Consolidate recording/artifact path logic
- Remove redundant manifest generation

**Result**: 549 → 440 lines (-109 lines, -20%)

## Expected Outcomes

- **Total Reduction**: 2827 → ~2200 lines (-627 lines, -22%)
- **Quality**: Single source of truth for config resolution
- **Maintainability**: Easier to extend with new config sources
- **Testability**: Modular, independently testable components
- **Performance**: Consolidated caching, single artifact write per init

## Timeline

- **Analysis & Design**: ✅ 30 min (complete)
- **Implementation**: 2-2.5 hours
  - `_core` modules: 45 min
  - Refactor feature_flags: 30 min
  - Refactor multi_env_loader: 30 min
  - Consolidate parsers: 30 min
  - Update artifact_manager: 20 min
- **Testing**: 1.5 hours
- **Validation & Push**: 30 min

**Total**: ~4.5 hours

## Testing Strategy

1. **Existing tests must pass**: 100% (Phase 1-3 regressions)
2. **New tests**: `_core` module unit tests
3. **Integration tests**: Consolidated config loading flow
4. **CI validation**: `pytest -m ci_safe` with 0 failures

## Acceptance Criteria

- [ ] No public API changes
- [ ] All existing tests pass
- [ ] 30-40% reduction achieved (2200 lines target)
- [ ] Performance within 10% of baseline
- [ ] Code coverage maintained
- [ ] Phase 1-3 functionality preserved

---

**Ready to begin Phase 4 implementation?**
