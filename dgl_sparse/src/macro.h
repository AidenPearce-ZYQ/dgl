/**
 * Copyright (c) 2023 by Contributors
 * @file macro.h
 * @brief DGL C++ sparse API macros.
 */
#ifndef DGL_SPARSE_MACRO_H_
#define DGL_SPARSE_MACRO_H_

namespace dgl {
namespace sparse {

/**
 * Dispatch an operator to a templated implementation function
 * according to its device:
 *
 * DGL_SPARSE_XPU_SWITCH(tensor.device().type(), XPU, {
 *   // Now XPU is a placeholder for tensor.device().type()
 *   DeviceSpecificImplementation<XPU>(...);
 * });
 */
#define DGL_SPARSE_XPU_SWITCH(device, XPU, op, ...)             \
  do {                                                          \
    if ((device) == c10::DeviceType::CPU) {                     \
      constexpr auto XPU = c10::DeviceType::CPU;                \
      { __VA_ARGS__ }                                           \
    } else {                                                    \
      LOG(FATAL) << "Operator " << (op) << " does not support " \
                 << c10::DeviceTypeName(device) << " device.";  \
    }                                                           \
  } while (0)

/**
 * Dispatch according to ID type (either int32 or int64):
 *
 * DGL_SPARSE_ID_TYPE_SWITCH(tensor.dtype(), IdType, {
 *   // Now IdType is the type corresponding to data type of the tensor.
 *   // For instance, one can do this for a CPU array:
 *   IdType *data = static_cast<IdType *>(array.data_ptr());
 * });
 */
#define DGL_SPARSE_ID_TYPE_SWITCH(dtype, IdType, op, ...)       \
  do {                                                          \
    if ((dtype) == torch::kInt32) {                             \
      typedef int32_t IdType;                                   \
      { __VA_ARGS__ }                                           \
    } else if ((dtype) == torch::kInt64) {                      \
      typedef int64_t IdType;                                   \
      { __VA_ARGS__ }                                           \
    } else {                                                    \
      LOG(FATAL) << "Operator " << (op) << " does not support " \
                 << (dtype).name() << " as ID dtype.";          \
    }                                                           \
  } while (0)

// Macro to dispatch according to device and index type.
#define DGL_SPARSE_COO_SWITCH(coo, XPU, IdType, op, ...)         \
  DGL_SPARSE_XPU_SWITCH(coo->indices.device().type(), XPU, op, { \
    DGL_SPARSE_ID_TYPE_SWITCH(                                   \
        (coo)->indices.dtype(), IdType, op, {{__VA_ARGS__}});    \
  });

}  // namespace sparse
}  // namespace dgl

#endif  // DGL_SPARSE_MACRO_H_
