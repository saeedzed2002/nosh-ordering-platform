import type { components, paths } from "./generated/v1";

/**
 * Stable frontend aliases for the checked-in `/api/v1` OpenAPI contract.
 * Regenerate the source file instead of editing its generated definitions.
 */
export type ApiV1Paths = paths;
export type ApiV1Schemas = components["schemas"];
export type ApiV1Availability = ApiV1Schemas["AvailabilityState"];
export type ApiV1Allergen = ApiV1Schemas["AllergenResponse"];
export type ApiV1CartQuote = ApiV1Schemas["CartQuoteResponse"];
export type ApiV1CartQuoteLine = ApiV1Schemas["CartQuoteLineResponse"];
export type ApiV1CartSelectedOption = ApiV1Schemas["CartSelectedOptionResponse"];
export type ApiV1Category = ApiV1Schemas["CategoryResponse"];
export type ApiV1Location = ApiV1Schemas["LocationResponse"];
export type ApiV1Media = ApiV1Schemas["MediaSummary"];
export type ApiV1MenuItem = ApiV1Schemas["MenuItemResponse"];
export type ApiV1Option = ApiV1Schemas["OptionResponse"];
export type ApiV1OptionGroup = ApiV1Schemas["OptionGroupResponse"];
export type ApiV1PublicReview = ApiV1Schemas["PublicReviewResponse"];
export type ApiV1PublicReviewList = ApiV1Schemas["PublicReviewListResponse"];
