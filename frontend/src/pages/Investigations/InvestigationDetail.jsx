import React, { useEffect, useState, useCallback } from 'react';
import { useParams, Link } from 'react-router-dom';
import { useSelector, useDispatch } from 'react-redux';
import {
  fetchInvestigationById,
  fetchInvestigationRCA,
  fetchInvestigationEvidence,
  fetchInvestigationCAPA,
  updateInvestigationDetails,
  updateFiveWhysLevel,
  addFishboneCause,
  updateFishboneCauseStatus,
  removeFishboneCause,
  addEvidenceItem,
  updateEvidenceStatus,
  updateCAPA,
} from '../../redux/slices/investigationSlice';
import investigationService from '../../services/investigationService';
import InvestigationHeader from '../../components/investigation/InvestigationHeader';
import InvestigationTabs from '../../components/investigation/InvestigationTabs';
import FiveWhysAnalysis from '../../components/investigation/FiveWhysAnalysis';
import FishboneAnalysis from '../../components/investigation/FishboneAnalysis';
import EvidenceList from '../../components/investigation/EvidenceList';
import CAPAForm from '../../components/investigation/CAPAForm';
import { Card, CardHeader, CardTitle, CardDescription, CardContent, CardFooter } from '../../components/common/Card';
import Input from '../../components/common/Input';
import StatusBadge from '../../components/common/StatusBadge';
import Button from '../../components/common/Button';
import LoadingSpinner from '../../components/common/LoadingSpinner';
import EmptyState from '../../components/common/EmptyState';
import {
  Save,
  CheckCircle2,
  AlertCircle,
  RotateCcw,
  ArrowLeft,
} from 'lucide-react';

/**
 * RootIQ Comprehensive Investigation Workspace supporting Overview, RCA, Evidence, and CAPA.
 * Fully integrated with the FastAPI backend and PostgreSQL database.
 */
export default function InvestigationDetailPage() {
  const { id } = useParams();
  const dispatch = useDispatch();

  const {
    currentInvestigation,
    detailLoading,
    detailError,
    detailStatusCode,
  } = useSelector((state) => state.investigations);

  const [activeTab, setActiveTab] = useState('overview');
  const [rcaSubMethod, setRcaSubMethod] = useState('5whys'); // '5whys' | 'fishbone'
  const [overviewSavedToast, setOverviewSavedToast] = useState(false);
  const [isSaving, setIsSaving] = useState(false);
  const [saveError, setSaveError] = useState(null);

  // Local state for editable Overview tab fields
  const [overviewForm, setOverviewForm] = useState({
    title: '',
    batch: '',
    department: '',
    productName: '',
    equipment: '',
    description: '',
    immediateAction: '',
    expectedCondition: '',
    actualCondition: '',
    observedImpact: '',
  });

  const loadData = useCallback(() => {
    if (id) {
      dispatch(fetchInvestigationById(id));
      dispatch(fetchInvestigationRCA(id));
      dispatch(fetchInvestigationEvidence(id));
      dispatch(fetchInvestigationCAPA(id));
    }
  }, [id, dispatch]);

  useEffect(() => {
    loadData();
  }, [loadData]);

  useEffect(() => {
    if (currentInvestigation) {
      setOverviewForm({
        title: currentInvestigation.title || currentInvestigation.incident_title || '',
        batch: currentInvestigation.batch || currentInvestigation.batch_number || '',
        department: currentInvestigation.department || '',
        productName: currentInvestigation.productName || currentInvestigation.product_name || '',
        equipment: currentInvestigation.equipment || '',
        description:
          currentInvestigation.incidentInfo?.incidentDescription ||
          currentInvestigation.incident_description ||
          '',
        immediateAction:
          currentInvestigation.incidentInfo?.immediateActionTaken ||
          currentInvestigation.immediate_action_taken ||
          '',
        expectedCondition:
          currentInvestigation.context?.expectedCondition ||
          currentInvestigation.expected_condition ||
          '',
        actualCondition:
          currentInvestigation.context?.actualCondition ||
          currentInvestigation.actual_condition ||
          '',
        observedImpact:
          currentInvestigation.context?.observedImpact ||
          currentInvestigation.observed_impact ||
          '',
      });
    }
  }, [currentInvestigation]);

  const handleOverviewChange = (field, value) => {
    setOverviewForm((prev) => ({ ...prev, [field]: value }));
  };

  const handleSaveOverview = async () => {
    if (!id) return;
    setIsSaving(true);
    setSaveError(null);

    const updatePayload = {
      incident_title: overviewForm.title,
      batch_number: overviewForm.batch,
      department: overviewForm.department,
      product_name: overviewForm.productName,
      equipment: overviewForm.equipment,
      incident_description: overviewForm.description,
      immediate_action_taken: overviewForm.immediateAction,
      expected_condition: overviewForm.expectedCondition,
      actual_condition: overviewForm.actualCondition,
      observed_impact: overviewForm.observedImpact,
    };

    try {
      await investigationService.updateInvestigation(id, updatePayload);
      dispatch(
        updateInvestigationDetails({
          id,
          incidentInfo: {
            incidentTitle: overviewForm.title,
            batchNumber: overviewForm.batch,
            department: overviewForm.department,
            productName: overviewForm.productName,
            equipment: overviewForm.equipment,
            incidentDescription: overviewForm.description,
            immediateActionTaken: overviewForm.immediateAction,
          },
          context: {
            expectedCondition: overviewForm.expectedCondition,
            actualCondition: overviewForm.actualCondition,
            observedImpact: overviewForm.observedImpact,
          },
        })
      );
      setOverviewSavedToast(true);
      setTimeout(() => setOverviewSavedToast(false), 3000);
    } catch (err) {
      setSaveError(err.message || 'Failed to save changes to the backend database.');
    } finally {
      setIsSaving(false);
    }
  };

  // 1. Loading State
  if (detailLoading) {
    return (
      <div className="py-24 flex flex-col items-center justify-center space-y-3">
        <LoadingSpinner size="lg" />
        <p className="text-sm font-semibold text-[#142B45]">Loading investigation workspace...</p>
        <p className="text-xs text-[#64748B]">Querying deviation record {id} from PostgreSQL database</p>
      </div>
    );
  }

  // 2. 404 Not Found State
  if (detailStatusCode === 404 || (!currentInvestigation && detailError && detailError.includes('not found'))) {
    return (
      <div className="py-16 max-w-xl mx-auto">
        <EmptyState
          title="Investigation Not Found"
          description={`Investigation '${id}' could not be found in the quality registry. It may have been archived or the ID may be mistyped.`}
          action={
            <Link to="/investigations">
              <Button variant="primary" size="sm" leftIcon={ArrowLeft}>
                Return to Investigations Registry
              </Button>
            </Link>
          }
        />
      </div>
    );
  }

  // 3. Error State (Server / Network Offline)
  if (detailError && !currentInvestigation) {
    return (
      <div className="py-16 max-w-xl mx-auto space-y-4">
        <div className="p-6 rounded-xl border border-[#FECACA] bg-[#FEF2F2] text-center space-y-3">
          <AlertCircle className="w-10 h-10 text-[#DC2626] mx-auto" />
          <h3 className="text-base font-bold text-[#991B1B]">Unable to Load Investigation</h3>
          <p className="text-xs text-[#B91C1C] max-w-md mx-auto">{detailError}</p>
          <div className="pt-2 flex items-center justify-center gap-2">
            <Button variant="secondary" size="sm" leftIcon={RotateCcw} onClick={loadData}>
              Retry Connection
            </Button>
            <Link to="/investigations">
              <Button variant="ghost" size="sm" leftIcon={ArrowLeft}>
                Back to List
              </Button>
            </Link>
          </div>
        </div>
      </div>
    );
  }

  if (!currentInvestigation) {
    return null;
  }

  return (
    <div className="space-y-6">
      {/* Workspace Header with Stepper and Metadata */}
      <InvestigationHeader
        investigation={currentInvestigation}
        activeTab={activeTab}
        onTabChange={setActiveTab}
      />

      {/* Main Tabs Navigation */}
      <InvestigationTabs
        activeTab={activeTab}
        onTabChange={setActiveTab}
      />

      {/* TAB 1: INCIDENT OVERVIEW */}
      {activeTab === 'overview' && (
        <div className="space-y-6">
          <Card>
            <CardHeader>
              <div>
                <CardTitle>Manufacturing Incident Record</CardTitle>
                <CardDescription>
                  Verified details, affected batches, and immediate containment measures (Database Persisted)
                </CardDescription>
              </div>
              <StatusBadge variant="teal" size="sm">
                ALCOA+ Traceable
              </StatusBadge>
            </CardHeader>

            <CardContent className="space-y-4">
              {saveError && (
                <div className="p-3 rounded-lg border border-[#FECACA] bg-[#FEF2F2] text-xs text-[#991B1B] flex items-center space-x-2">
                  <AlertCircle className="w-4 h-4 shrink-0 text-[#DC2626]" />
                  <span>{saveError}</span>
                </div>
              )}

              <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
                <Input
                  label="Deviation Reference ID"
                  value={currentInvestigation.incidentInfo?.deviationId || `DEV-${id}`}
                  disabled
                />
                <Input
                  label="Production Batch Number"
                  value={overviewForm.batch}
                  onChange={(e) => handleOverviewChange('batch', e.target.value)}
                  required
                />
                <Input
                  label="API Product Name"
                  value={overviewForm.productName}
                  onChange={(e) => handleOverviewChange('productName', e.target.value)}
                  required
                />
              </div>

              <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
                <Input
                  label="Manufacturing Department"
                  value={overviewForm.department}
                  onChange={(e) => handleOverviewChange('department', e.target.value)}
                  required
                />
                <Input
                  label="Equipment / Unit Identifier"
                  value={overviewForm.equipment}
                  onChange={(e) => handleOverviewChange('equipment', e.target.value)}
                  required
                />
              </div>

              <div>
                <label className="block text-xs font-semibold text-[#142B45] mb-1.5 uppercase tracking-wider">
                  Incident Narrative / Observation
                </label>
                <textarea
                  rows={3}
                  value={overviewForm.description}
                  onChange={(e) => handleOverviewChange('description', e.target.value)}
                  className="block w-full rounded-lg border border-[#CBD5E1] text-sm p-3 bg-white focus:border-[#0F9D91] focus:ring-2 focus:ring-[#0F9D91]/20 leading-relaxed"
                />
              </div>

              <div>
                <label className="block text-xs font-semibold text-[#142B45] mb-1.5 uppercase tracking-wider">
                  Immediate Containment Action Taken
                </label>
                <textarea
                  rows={2}
                  value={overviewForm.immediateAction}
                  onChange={(e) => handleOverviewChange('immediateAction', e.target.value)}
                  className="block w-full rounded-lg border border-[#CBD5E1] text-sm p-3 bg-white focus:border-[#0F9D91] focus:ring-2 focus:ring-[#0F9D91]/20 leading-relaxed"
                />
              </div>

              <div className="grid grid-cols-1 sm:grid-cols-3 gap-4 pt-2">
                <Input
                  label="Expected Condition (Spec)"
                  value={overviewForm.expectedCondition}
                  onChange={(e) => handleOverviewChange('expectedCondition', e.target.value)}
                />
                <Input
                  label="Actual Condition (Excursion)"
                  value={overviewForm.actualCondition}
                  onChange={(e) => handleOverviewChange('actualCondition', e.target.value)}
                />
                <Input
                  label="Observed Impact"
                  value={overviewForm.observedImpact}
                  onChange={(e) => handleOverviewChange('observedImpact', e.target.value)}
                />
              </div>
            </CardContent>

            <CardFooter className="py-3 bg-[#F8FAFC]">
              <div className="text-xs text-[#64748B]">
                {overviewSavedToast ? (
                  <span className="text-[#059669] font-semibold flex items-center">
                    <CheckCircle2 className="w-4 h-4 mr-1" /> Investigation Details Saved in Database
                  </span>
                ) : (
                  <span>Modifications persist in PostgreSQL across investigation sessions.</span>
                )}
              </div>

              <div className="flex items-center space-x-2">
                <Button
                  variant="primary"
                  size="sm"
                  leftIcon={Save}
                  onClick={handleSaveOverview}
                  disabled={isSaving}
                >
                  {isSaving ? 'Saving...' : 'Save Overview Details'}
                </Button>
                <Button
                  variant="accent"
                  size="sm"
                  onClick={() => setActiveTab('rca')}
                >
                  Proceed to RCA &rarr;
                </Button>
              </div>
            </CardFooter>
          </Card>
        </div>
      )}

      {/* TAB 2: ROOT CAUSE ANALYSIS (5-WHYS & 6M ISHIKAWA) */}
      {activeTab === 'rca' && (
        <div className="space-y-6">
          {/* Sub-method switcher */}
          <div className="flex items-center justify-between p-3.5 bg-white rounded-xl border border-[#E2E8F0] shadow-2xs">
            <div className="flex items-center space-x-2">
              <span className="text-xs font-bold text-[#142B45] uppercase tracking-wider mr-2">
                Causal Method:
              </span>
              <button
                type="button"
                onClick={() => setRcaSubMethod('5whys')}
                className={`px-3 py-1.5 rounded-lg text-xs font-semibold transition ${
                  rcaSubMethod === '5whys'
                    ? 'bg-[#142B45] text-white shadow-2xs'
                    : 'bg-[#F1F5F9] text-[#64748B] hover:text-[#142B45]'
                }`}
              >
                5-Whys Analysis Chain
              </button>
              <button
                type="button"
                onClick={() => setRcaSubMethod('fishbone')}
                className={`px-3 py-1.5 rounded-lg text-xs font-semibold transition ${
                  rcaSubMethod === 'fishbone'
                    ? 'bg-[#142B45] text-white shadow-2xs'
                    : 'bg-[#F1F5F9] text-[#64748B] hover:text-[#142B45]'
                }`}
              >
                6M Ishikawa (Fishbone) Matrix
              </button>
            </div>

            <StatusBadge variant="teal" size="sm">
              {rcaSubMethod === '5whys' ? 'Linear Causal Path' : 'Multi-Factor 6M Matrix'}
            </StatusBadge>
          </div>

          {rcaSubMethod === '5whys' ? (
            <FiveWhysAnalysis
              fiveWhys={currentInvestigation.fiveWhys || []}
              onSaveLevel={(idx, levelData) =>
                dispatch(updateFiveWhysLevel({ id, levelIndex: idx, ...levelData }))
              }
              onSaveAll={() => {}}
            />
          ) : (
            <FishboneAnalysis
              fishbone={currentInvestigation.fishbone || {}}
              onAddCause={(category, cause, status) =>
                dispatch(addFishboneCause({ id, category, cause, status }))
              }
              onUpdateCauseStatus={(category, causeId, status) =>
                dispatch(updateFishboneCauseStatus({ id, category, causeId, status }))
              }
              onRemoveCause={(category, causeId) =>
                dispatch(removeFishboneCause({ id, category, causeId }))
              }
            />
          )}
        </div>
      )}

      {/* TAB 3: EVIDENCE & GAPS */}
      {activeTab === 'evidence' && (
        <EvidenceList
          evidence={currentInvestigation.evidence || []}
          onAddEvidence={(item) => dispatch(addEvidenceItem({ id, item }))}
          onUpdateEvidenceStatus={(evidenceId, status) =>
            dispatch(updateEvidenceStatus({ id, evidenceId, status }))
          }
        />
      )}

      {/* TAB 4: CAPA PLAN */}
      {activeTab === 'capa' && (
        <CAPAForm
          capa={currentInvestigation.capa || {}}
          onSaveCAPA={(capaData) => dispatch(updateCAPA({ id, capa: capaData }))}
        />
      )}
    </div>
  );
}
