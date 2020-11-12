#ifndef DECTREE_H
#define DECTREE_H


typedef enum {
  BND_BOTH_SIDES;
  BND_LOWER_BOUND;
  BND_UPPER_BOUND;
} leaf_bound_type_t;

typedef struct {
  calib_field_t calib;
  uint8_t lower;
  uint8_t upper;
  leaf_bound_type_t bnd;
} leaf_bound_t;

typedef struct {
  leaf_bound_t bounds[MAX_DEPTH];
  leaf_model_t model;
  uint8_t n_bounds;
} leaf_t;

int get_num_samples(leaf_t& node);
uint8_t get_random_value(leaf_t& node, calib_field_t& field, uint8_t lower, uint8_t upper);
void initialize_leaf(leaf_t& leaf);
void add_leaf_bound(leaf_t& leaf, uint8_t lower, uint8_t upper, leaf_bound_type_t bnd);




#endif #DECTREE_H
